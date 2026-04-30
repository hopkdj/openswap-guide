---
title: "Uyuni vs Foreman vs Salt Stack: Self-Hosted Patch Management Guide 2026"
date: 2026-05-02
tags: ["comparison", "guide", "self-hosted", "patch-management", "uyuni", "foreman", "salt-stack", "security", "infrastructure"]
draft: false
description: "Compare Uyuni, Foreman, and Salt Stack for self-hosted patch management. Complete deployment guide with Docker configs, feature comparison, and setup instructions for keeping your servers up to date in 2026."
---

Keeping servers patched and up to date is one of the most fundamental — and most neglected — operational tasks in any infrastructure. Unpatched systems are the single largest attack vector for ransomware, data breaches, and compliance failures. Commercial patch management platforms from vendors like Tivoli, ManageEngine, and Automox charge per-node licensing fees that quickly become unsustainable at scale, while also requiring your vulnerability data to flow through cloud infrastructure.

Self-hosted patch management tools give you full control over your update pipeline: decide which patches to test, when to deploy them, and how to roll back if something breaks. In this guide, we compare three mature open-source platforms built for exactly this purpose: **Uyuni** (554 stars, actively developed by SUSE), **Foreman** (2,858 stars, the lifecycle management engine behind Red Hat Satellite), and **Salt Stack** (15,363 stars, VMware's configuration management and remote execution framework).

## Why Self-Hosted Patch Management Matters

Running your own patch management infrastructure addresses several critical operational and security requirements:

- **Complete control over the update pipeline**: Decide which patches land in which environment, with full testing windows and rollback capabilities. No vendor decides your patching schedule.
- **Air-gapped network support**: Defense, healthcare, and financial sectors operate isolated networks that cannot reach public package repositories. Self-hosted tools mirror repositories locally.
- **Audit and compliance**: Every patch applied (or deferred) is logged locally. PCI-DSS, HIPAA, SOC 2, and ISO 27001 auditors want to see patch management records — self-hosted tools keep them under your control.
- **Cost at scale**: Per-node pricing models become expensive for organizations managing hundreds or thousands of endpoints. Self-hosted tools use your existing compute resources.
- **Bandwidth optimization**: Instead of every server downloading packages from the internet, a local mirror serves them once and distributes to all managed nodes.

## Quick Comparison Table

| Feature | Uyuni | Foreman | Salt Stack |
|---|---|---|---|
| **Primary Focus** | Systems management & patching | Lifecycle management & provisioning | Configuration management & remote execution |
| **Origins** | Fork of Spacewalk (SUSE) | Red Hat ecosystem | VMware |
| **Language** | Java (backend), Python (agents) | Ruby (backend), Python/ERB (templates) | Python |
| **Package Support** | RPM, DEB, SUSE | RPM, DEB | RPM, DEB, Solaris, macOS, Windows |
| **Web UI** | Built-in (SUSE Manager UI) | Built-in (Foreman Web UI) | Salt GUI (separate project) |
| **Agent** | salt-minion | puppet-agent, salt-minion, or SSH | salt-minion |
| **Patch Scheduling** | Yes (maintenance windows) | Yes (via Remote Execution) | Yes (via schedule module) |
| **Vulnerability Scanning** | CVE mapping via SUSE CVRF | Via plugins (OpenSCAP) | Via grains/modules (external tools) |
| **Container Support** | Docker, Podman | Docker, Podman, Kubernetes | Docker, Podman, Kubernetes |
| **Docker Deployment** | Official images available | Docker Compose available | Docker image available |
| **GitHub Stars** | 554 | 2,858 | 15,363 |
| **Last Update** | April 2026 | April 2026 | April 2026 |

## Uyuni: The SUSE Systems Management Platform

Uyuni is the open-source upstream of SUSE Manager, forked from the original Spacewalk project. It provides a comprehensive web-based interface for managing patches, software channels, configuration files, and system groups across large fleets of Linux servers.

Uyuni's strength lies in its mature repository mirroring capabilities. It can mirror CentOS, Debian, Ubuntu, SUSE, and openSUSE repositories, then serve them to managed clients over a local network. The web UI provides detailed patch advisory views, showing which CVEs affect which systems and whether patches are available.

### Uyuni Docker Compose Deployment

Uyuni provides official container images. Here is a production-oriented Docker Compose configuration based on the official deployment documentation:

```yaml
version: "3.8"

services:
  uyuni-server:
    image: registry.opensuse.org/uyuni/server/uyuni-server:latest
    container_name: uyuni-server
    hostname: uyuni.example.com
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - uyuni-data:/var/lib/uyuni
      - uyuni-ssl:/root/ssl-build
      - uyuni-pgsql:/var/lib/pgsql
      - /var/lib/cobbler:/var/lib/cobbler
    environment:
      - TZ=UTC
      - UYUNI_MGR_SYNC=yes
    restart: unless-stopped

  uyuni-proxy:
    image: registry.opensuse.org/uyuni/server/uyuni-proxy:latest
    container_name: uyuni-proxy
    ports:
      - "80:80"
      - "443:443"
      - "4848:4848"
    volumes:
      - uyuni-proxy-data:/var/lib/uyuni-proxy
    environment:
      - SERVER_HOSTNAME=uyuni.example.com
    depends_on:
      - uyuni-server
    restart: unless-stopped

volumes:
  uyuni-data:
  uyuni-ssl:
  uyuni-pgsql:
  uyuni-proxy-data:
```

For initial setup, Uyuni requires a bootstrap process that generates SSL certificates and configures the PostgreSQL database:

```bash
# Initialize Uyuni server (first run only)
docker exec -it uyuni-server \
  mgr-setup --non-interactive \
  --admin-user admin \
  --admin-password YOUR_SECURE_PASSWORD \
  --org-name "Your Organization"

# Sync repositories after setup
docker exec -it uyuni-server \
  mgr-sync refresh --refresh-channels
```

The `mgr-sync` tool handles repository synchronization — it downloads package metadata, errata, and CVE mappings from upstream repositories. You schedule this via cron for automatic daily updates.

### Key Uyuni Features

- **Content Lifecycle Management**: Create development, testing, and production channels. Promote patches through environments after validation.
- **System Groups and Activation Keys**: Register systems with pre-configured activation keys that auto-assign channels and configuration profiles.
- **SCAP Compliance Scanning**: Integrate OpenSCAP to audit systems against security benchmarks (CIS, STIG).
- **Hardware Inventory**: Collect and report hardware details from managed systems for capacity planning.

## Foreman: The Lifecycle Management Engine

Foreman is the upstream project behind Red Hat Satellite and has been a cornerstone of Linux infrastructure management since 2009. While often associated with provisioning (PXE boot, cloud instance creation), Foreman's patch management capabilities through its Smart Proxy and Remote Execution plugins are production-ready.

Foreman's architecture is plugin-driven. The core handles host inventory and classification, while plugins add capabilities:

- **Katello**: Adds content management (repositories, errata, packages, Docker images). This is the patch management engine.
- **Remote Execution**: Runs commands (including package updates) on managed hosts via SSH — no agent required.
- **Puppet Integration**: Optional Puppet agent support for configuration drift detection.

### Foreman Docker Compose Deployment

Foreman provides an official all-in-one Docker image with Katello included. This deployment uses PostgreSQL and Redis as separate services:

```yaml
version: "3.8"

services:
  foreman:
    image: theforeman/foreman:3.11-katello-4.13
    container_name: foreman
    hostname: foreman.example.com
    ports:
      - "80:80"
      - "443:443"
      - "8443:8443"
      - "8140:8140"
      - "9090:9090"
    volumes:
      - foreman-data:/var/lib/foreman
      - foreman-puppet:/etc/puppetlabs
      - foreman-config:/etc/foreman
      - foreman-logs:/var/log/foreman
      - foreman-certs:/etc/pki/katello
    environment:
      - FOREMAN_CLI_USERNAME=admin
      - FOREMAN_CLI_PASSWORD=YOUR_SECURE_PASSWORD
      - FOREMAN_OAUTH_CONSUMER_KEY=foreman
      - FOREMAN_OAUTH_CONSUMER_SECRET=foreman_secret
      - RAILS_ENV=production
    restart: unless-stopped

  postgresql:
    image: docker.io/library/postgres:15
    container_name: foreman-db
    volumes:
      - foreman-db-data:/var/lib/postgresql/data
    environment:
      - POSTGRESQL_DATABASE=foreman
      - POSTGRESQL_USER=foreman
      - POSTGRESQL_PASSWORD=foreman_db_password
    restart: unless-stopped

  redis:
    image: docker.io/library/redis:7-alpine
    container_name: foreman-redis
    volumes:
      - foreman-redis-data:/data
    restart: unless-stopped

volumes:
  foreman-data:
  foreman-puppet:
  foreman-config:
  foreman-logs:
  foreman-certs:
  foreman-db-data:
  foreman-redis-data:
```

After the initial deployment, configure content views and lifecycle environments:

```bash
# Create a lifecycle environment chain
hammer lifecycle-environment create \
  --organization "Default Organization" \
  --name "Development" \
  --description "Development patch testing" \
  --prior "Library"

hammer lifecycle-environment create \
  --organization "Default Organization" \
  --name "Production" \
  --description "Production patches" \
  --prior "Development"

# Create a content view for patch filtering
hammer content-view create \
  --name "Security Patches" \
  --description "Only security errata" \
  --organization "Default Organization"
```

### Key Foreman Features

- **Content Views**: Filter patches by type (security, bugfix, enhancement), date range, or specific errata IDs. Publish filtered views to lifecycle environments.
- **Host Collection Management**: Group hosts by role, environment, or criticality. Apply patches to entire collections at once.
- **Remote Execution Templates**: Customize update commands per OS — `dnf update --security` for RHEL, `apt-get upgrade` for Debian, `zypper patch` for SUSE.
- **Audit Trail**: Every patch applied is logged with who initiated it, which host, and the result. Exportable for compliance reporting.

## Salt Stack: The Remote Execution Framework

Salt Stack (Salt) takes a fundamentally different approach from Uyuni and Foreman. Rather than being a dedicated patch management platform, Salt is a configuration management and remote execution engine that uses its `pkg` state module and `salt-minion` architecture to manage packages at massive scale.

Salt's event-driven architecture makes it uniquely suited for automated patching workflows. You can set up reactors that trigger when a new CVE is published, automatically testing and deploying patches across your infrastructure based on predefined rules.

### Salt Stack Docker Compose Deployment

Salt provides an official Docker image for the master. Managed minions run on each target host:

```yaml
version: "3.8"

services:
  salt-master:
    image: saltstack/salt:latest
    container_name: salt-master
    hostname: salt-master.example.com
    command: salt-master -l info
    ports:
      - "4505:4505"
      - "4506:4506"
      - "8000:8000"
    volumes:
      - salt-master-config:/etc/salt
      - salt-master-pki:/etc/salt/pki
      - salt-master-cache:/var/cache/salt
      - salt-master-jobs:/var/cache/salt/master/jobs
    environment:
      - SALT_MASTER_CONFIG=/etc/salt/master
    restart: unless-stopped

  salt-api:
    image: saltstack/salt:latest
    container_name: salt-api
    command: salt-api -l info
    ports:
      - "8000:8000"
    volumes:
      - salt-master-config:/etc/salt
      - salt-master-pki:/etc/salt/pki
    depends_on:
      - salt-master
    restart: unless-stopped

volumes:
  salt-master-config:
  salt-master-pki:
  salt-master-cache:
  salt-master-jobs:
```

Configure the Salt master for patch management in `/etc/salt/master`:

```yaml
# /etc/salt/master
external_auth:
  pam:
    patchadmin:
      - '.*':
        - pkg.*
        - state.apply
        - test.ping

# Schedule security patching every Sunday at 2 AM
schedule:
  security_patches:
    function: state.apply
    args:
      - patching.security
    when: Sunday 2:00 AM
    maxrunning: 1
    return_job: True
```

On each minion, the patching state file (`/srv/salt/patching/security.sls`) defines what gets updated:

```yaml
# /srv/salt/patching/security.sls
security_updates:
  pkg.uptodate:
    - refresh: True
    - dist_upgrade: True
    - hold_pkgs:
      - kernel
      - linux-image
    - skip_verify: False
```

### Key Salt Stack Features

- **Targeting Engine**: Select hosts by grain (OS version, datacenter, role), pillar (custom data), or compound expressions. `salt -G 'os:Ubuntu' pkg.list_upgrades` shows pending updates for all Ubuntu hosts.
- **Event-Driven Reactors**: Set up reactors that automatically test patches on a staging group, then promote to production if tests pass.
- **Mine Functions**: Collect and report package versions from all minions, building a real-time inventory of installed software across your fleet.
- **Orchestration Runner**: Run multi-step patching workflows — drain load balancer, apply patches, reboot, run health checks, rejoin pool.

## Choosing the Right Tool

| Criteria | Choose Uyuni If... | Choose Foreman If... | Choose Salt Stack If... |
|---|---|---|---|
| **Your OS ecosystem** | Primarily SUSE/openSUSE + RPM/DEB | Primarily RHEL/CentOS + Katello integration needed | Mixed OS (Linux, macOS, Windows, network devices) |
| **Scale** | Up to 10,000 managed systems | Up to 50,000 managed systems | 100,000+ with Salt's event-driven architecture |
| **Patch workflow** | Channel-based lifecycle (dev → test → prod) | Content views + lifecycle environments | State-driven with reactor automation |
| **Vulnerability tracking** | Built-in CVE mapping via CVRF | Via OpenSCAP plugin + Katello errata | Via external CVE feeds + Salt grains |
| **Team familiarity** | SUSE Manager experience | Red Hat Satellite experience | Configuration management / DevOps background |
| **Learning curve** | Moderate (web UI driven) | Steeper (Katello complexity) | Moderate (YAML states, Python) |

## FAQ

### What is the difference between patch management and configuration management?

Patch management focuses specifically on keeping software packages and security updates current across your systems. Configuration management handles broader system state — file contents, service configurations, user accounts, and software installation. Tools like Salt Stack do both, while Uyuni and Foreman are more focused on package and patch lifecycle management.

### Can I use Salt Stack without installing an agent on every server?

Yes. Salt supports SSH-based execution via `salt-ssh`, which requires no persistent agent on managed hosts. However, you lose real-time event streaming and the mine function. For regular patch management, the `salt-minion` agent is recommended because it maintains a persistent connection to the master for fast command delivery.

### How does Uyuni handle offline or air-gapped networks?

Uyuni is specifically designed for disconnected environments. You can sync repositories on a machine with internet access, export them to removable media, and import them into an air-gapped Uyuni server. The `mgr-sync` tool supports export/import workflows for exactly this use case.

### Does Foreman support Windows patching?

Foreman with Katello primarily targets Linux systems (RHEL, CentOS, Debian, Ubuntu, SUSE). Windows support is limited — you can manage Windows hosts for provisioning and basic inventory, but patch deployment requires additional tooling (e.g., WSUS integration or Ansible Windows modules via Remote Execution).

### Which tool is easiest to set up for a small team managing 50 servers?

For a small team, Salt Stack typically has the fastest path to value. The master deploys in minutes via Docker, and the `pkg.uptodate` state handles patching across mixed Linux distributions with minimal configuration. Uyuni requires more initial setup (database, SSL certificates, repository channels), while Foreman's Katello plugin adds significant complexity that smaller deployments may not need.

### Can these tools roll back patches if something breaks?

Uyuni supports snapshot-based rollback through its integration with Btrfs and LVM snapshots on SUSE systems. Foreman can leverage Katello content view version switching — revert hosts to a previous content view that had the older package versions. Salt Stack doesn't have built-in rollback, but you can write states that pin specific package versions and revert on failure detection using Salt's event system.

## Final Recommendation

For **SUSE-centric environments**, Uyuni is the natural choice — it shares DNA with SUSE Manager and provides the most polished experience for SUSE package management. For **Red Hat/CentOS shops**, Foreman with Katello mirrors the Red Hat Satellite workflow with full open-source freedom. For **mixed-OS infrastructure** where patch management needs to scale across Linux, Windows, and network devices, Salt Stack's event-driven architecture and targeting engine make it the most flexible option.

Each tool can handle the core patch management workflow — mirror repositories, test patches, deploy to production, and audit results. The deciding factor is your existing infrastructure ecosystem and team expertise.

For related reading, see our [Ansible vs SaltStack vs Puppet configuration management comparison](../ansible-vs-saltstack-vs-puppet-configuration-management-2026/) and [Cockpit vs Webmin vs Ajenti server management guide](../2026-04-27-cockpit-vs-webmin-vs-ajenti-self-hosted-server-management-web-ui-guide-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Uyuni vs Foreman vs Salt Stack: Self-Hosted Patch Management Guide 2026",
  "description": "Compare Uyuni, Foreman, and Salt Stack for self-hosted patch management. Complete deployment guide with Docker configs, feature comparison, and setup instructions.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
