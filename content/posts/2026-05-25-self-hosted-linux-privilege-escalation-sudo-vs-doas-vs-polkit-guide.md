---
title: "Self-Hosted Linux Privilege Escalation Management: sudo vs doas vs polkit"
date: "2026-05-25"
tags: ["linux-system-administration", "security", "access-control", "privilege-management"]
draft: false
---

When managing self-hosted Linux servers, controlling who can execute privileged commands is a foundational security requirement. The default root account should never be used directly for day-to-day administration. Instead, privilege escalation tools provide audited, configurable, and constrained access to elevated permissions. Three dominant approaches have emerged in the Linux ecosystem: **sudo**, the ubiquitous standard; **doas**, the minimalist alternative from OpenBSD; and **polkit** (PolicyKit), the desktop-focused authorization framework that has found its way into server workflows.

This guide compares these three privilege escalation mechanisms across configuration complexity, security features, auditing capabilities, and deployment scenarios — helping you choose the right tool for your self-hosted infrastructure.

## Overview of Privilege Escalation Tools

Privilege escalation tools sit between regular users and the root account, enforcing policies that define which users or groups can run specific commands with elevated privileges. Each tool takes a fundamentally different approach to this problem.

### sudo — The Established Standard

**sudo** (superuser do) has been the default privilege escalation tool on most Linux distributions since the 1990s. It uses a rule-based configuration file (`/etc/sudoers`) that defines exactly which users can execute which commands as which target users. sudo supports extensive features including command whitelisting, environment variable control, session logging, timestamp caching, and plugin extensibility.

| Attribute | Value |
|-----------|-------|
| GitHub/Project | [sudo.ws](https://www.sudo.ws/) |
| License | ISC |
| Default on | Ubuntu, Debian, RHEL, CentOS, Arch, Fedora |
| Configuration | `/etc/sudoers` (visudo) |
| Last Update | Active development |

### doas — The Minimalist Alternative

**doas** (do as) originated in OpenBSD 5.8 as a replacement for sudo, designed to be simpler, smaller, and more secure by default. It was later ported to Linux via the `opendoas` project. doas uses a single configuration file (`/etc/doas.conf`) with straightforward syntax, has a much smaller codebase (~6,000 lines vs sudo's ~150,000 lines), and follows the principle of least privilege by design.

| Attribute | Value |
|-----------|-------|
| GitHub/Project | [openDoas](https://github.com/Duncaen/OpenDoas) |
| License | ISC |
| Default on | OpenBSD (native), available on most Linux distros |
| Configuration | `/etc/doas.conf` |
| Last Update | Active development |

### polkit — The Authorization Framework

**polkit** (PolicyKit) is not a direct sudo replacement but an application-level authorization framework. It determines whether an unprivileged process is allowed to perform a privileged operation. Unlike sudo, which is invoked interactively by a user, polkit operates as a daemon that applications query for authorization decisions. It is increasingly used in server contexts for managing system-level operations through D-Bus interfaces.

| Attribute | Value |
|-----------|-------|
| GitHub/Project | [freedesktop.org](https://gitlab.freedesktop.org/polkit/polkit) |
| License | LGPL-2.1+ |
| Default on | Most desktop Linux distributions, systemd-based servers |
| Configuration | `/etc/polkit-1/rules.d/` (JavaScript rules) |
| Last Update | Active development |

## Comparison Table

| Feature | sudo | doas | polkit |
|---------|------|------|--------|
| **Codebase size** | ~150,000 lines | ~6,000 lines | ~75,000 lines |
| **Configuration syntax** | Complex (sudoers DSL) | Simple (key-value) | JavaScript rules |
| **Default install** | Nearly universal | Manual install required | Pre-installed on most |
| **Command-level ACLs** | Yes (granular) | Yes (basic) | Via action IDs |
| **Password caching** | Yes (configurable timeout) | No (always prompts) | Yes (via auth agent) |
| **Logging/auditing** | Extensive (syslog, journald) | Basic (syslog) | Via journal |
| **Environment control** | Comprehensive (env_keep, env_reset) | Limited | N/A (not a shell tool) |
| **PAM integration** | Yes | Yes | Yes (native) |
| **Group-based rules** | Yes (`%groupname`) | Yes (`permit :group`) | Yes (via rule conditions) |
| **NOPASSWD support** | Yes | Yes (`nopass`) | Yes (via rules) |
| **Interactive use** | Primary use case | Primary use case | Not designed for it |
| **API/programmatic** | Via plugin | No | Via D-Bus |
| **Attack surface** | Large (complex config parser) | Small (simple parser) | Medium (D-Bus surface) |
| **Multi-factor auth** | Via PAM | Via PAM | Via auth agent |

## Configuration Examples

### sudo Configuration

The sudo configuration uses the `visudo` command to safely edit `/etc/sudoers`. Here are common patterns:

```bash
# Allow members of the 'admin' group full root access
%admin ALL=(ALL:ALL) ALL

# Allow 'deploy' user to run specific commands without password
deploy ALL=(root) NOPASSWD: /usr/bin/systemctl restart nginx, /usr/bin/systemctl reload nginx

# Allow 'backup' user to run rsync as root
backup ALL=(root) NOPASSWD: /usr/bin/rsync

# Command alias for database management
Cmnd_Alias DB_MGMT = /usr/bin/pg_dump, /usr/bin/pg_restore, /usr/bin/mysql, /usr/bin/mysqldump
dbadmin ALL=(root) DB_MGMT
```

Test the configuration syntax before saving:

```bash
visudo -c
# Output: /etc/sudoers: parsed OK
```

### doas Configuration

doas uses a much simpler syntax in `/etc/doas.conf`:

```bash
# Allow members of 'wheel' group full root access with password
permit persist :wheel

# Allow 'deploy' user to run specific commands without password
permit nopass deploy cmd systemctl args restart nginx
permit nopass deploy cmd systemctl args reload nginx

# Allow 'backup' user to run rsync as root
permit nopass backup cmd rsync

# Allow all users to run specific read-only commands
permit nopass keepenv cmd journalctl
permit nopass keepenv cmd systemctl args status *
```

The entire configuration is typically under 20 lines, compared to sudo configurations that can span hundreds of lines for complex setups.

### polkit Configuration

polkit uses JavaScript-based rule files in `/etc/polkit-1/rules.d/`:

```javascript
// 50-admin.rules - Allow admin group to manage services without authentication
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.systemd1.manage-units") === 0 &&
        subject.isInGroup("admin")) {
        return polkit.Result.YES;
    }
});

// 51-deploy.rules - Allow deploy user to restart specific services
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.systemd1.manage-units") === 0 &&
        subject.user === "deploy") {
        return polkit.Result.YES;
    }
});

// 52-audit.rules - Require authentication for destructive actions
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.freedesktop.systemd1.manage-units") === 0 &&
        action.lookup("verb") === "stop" &&
        !subject.isInGroup("admin")) {
        return polkit.Result.AUTH_ADMIN;
    }
});
```

Test polkit rules with:

```bash
pkaction --verbose | head -20
pkcheck --action-id org.freedesktop.systemd1.manage-units --process $$ --allow-user-interaction
```

## Security Considerations

### Attack Surface Comparison

The most significant security differentiator is codebase complexity. sudo's extensive feature set requires a complex configuration parser, which has been the source of multiple CVEs over the years (including CVE-2021-3156 "Baron Samedit" and CVE-2019-14287). doas's minimal codebase (~6,000 lines) presents a significantly smaller attack surface, making it easier to audit and less likely to contain parser vulnerabilities.

polkit operates differently — it is not invoked directly by users but runs as a system daemon. Its security model depends on the correctness of D-Bus communication and the JavaScript rule interpreter. While polkit has had its own vulnerabilities (CVE-2021-4115, CVE-2021-3560), the impact model differs from sudo since it requires an application to trigger the authorization check.

### Configuration Safety

sudo provides `visudo`, which locks the file and validates syntax before saving — preventing a broken configuration from locking administrators out. doas lacks an equivalent built-in validator; a syntax error in `/etc/doas.conf` can break all privilege escalation until fixed from a root shell. polkit rule files are JavaScript, so syntax errors only affect the specific rule file, not the entire system.

### Principle of Least Privilege

doas follows the principle of least privilege by default — rules must explicitly grant access, and the configuration is intentionally limited in scope. sudo allows very fine-grained control but also permits overly permissive configurations (`ALL=(ALL:ALL) ALL`) that undermine security. polkit requires explicit action ID matching, making over-permissive configurations less likely but also more complex to set up correctly.

## Docker and Container Deployment Examples

While these tools are system-level utilities, they are frequently configured inside container images and infrastructure-as-code:

```yaml
# Docker Compose: Pre-configured admin container with doas
version: "3.8"
services:
  admin-box:
    image: alpine:latest
    container_name: self-hosted-admin
    volumes:
      - ./doas.conf:/etc/doas.conf:ro
      - /var/run/docker.sock:/var/run/docker.sock
    command: >
      sh -c "
        apk add --no-cache opendoas sudo &&
        cp /etc/doas.conf /etc/doas.conf &&
        tail -f /dev/null
      "
    restart: unless-stopped
```

```yaml
# Docker Compose: polkit policy for container management
version: "3.8"
services:
  polkit-manager:
    image: debian:bookworm-slim
    container_name: polkit-config
    volumes:
      - ./polkit-rules:/etc/polkit-1/rules.d:ro
    command: >
      sh -c "
        apt-get update && apt-get install -y polkitd dbus &&
        mkdir -p /etc/polkit-1/rules.d &&
        cp /etc/polkit-1/rules.d/*.rules /etc/polkit-1/rules.d/ &&
        dbus-daemon --system --fork &&
        polkitd --no-debug &&
        tail -f /dev/null
      "
    restart: unless-stopped
```

## Choosing the Right Privilege Escalation Tool

The choice between sudo, doas, and polkit depends on your specific requirements:

- **Use sudo** when you need maximum compatibility, fine-grained command-level access control, extensive auditing, and are managing diverse Linux distributions. It is the safest choice for production servers where compatibility and audit trails are paramount.

- **Use doas** when you value simplicity, a smaller attack surface, and have straightforward privilege escalation needs. It excels in minimal server deployments, containers, and environments where configuration complexity is a liability.

- **Use polkit** when you need programmatic authorization for application-level operations, are building a management dashboard or API that needs to perform privileged actions, or are working within a systemd-centric infrastructure.

For most self-hosted server administrators, a hybrid approach works best: doas for interactive user privilege escalation (smaller attack surface, simpler config) combined with polkit for application-level authorization (D-Bus services, system management APIs). sudo remains the default choice when compatibility across dozens of distributions and legacy configurations is required.

## Why Self-Host Privilege Escalation Management?

Managing privilege escalation on your own servers gives you complete control over access policies, audit trails, and security configurations. When you rely on cloud-hosted management platforms or SaaS identity services, you surrender visibility into how access decisions are made and logged. Self-hosted privilege management ensures:

- **Complete audit visibility**: Every escalation attempt is logged locally, under your control. You can integrate with your own SIEM, log aggregation, and alerting infrastructure without depending on third-party log delivery pipelines.

- **No vendor lock-in**: sudo, doas, and polkit are open-source tools with decades of development history. They are not subject to subscription changes, feature deprecation, or company acquisitions.

- **Customizable security posture**: You define exactly who can do what, when, and under which conditions. Cloud-managed access control often imposes artificial limitations or forces you into predetermined policy templates.

For identity synchronization across multiple servers, see our [Apache Syncope vs midPoint vs LTB LDAP Toolbox guide](../2026-05-04-apache-syncope-vs-midpoint-vs-ltb-ldap-toolbox-self-hosted-identity-sync-guide/).
For network-level access control, check our [PacketFence vs OpenNAC vs Gatekeeper comparison](../2026-05-13-self-hosted-network-access-control-packetfence-opennac-gatekeeper-guide/).
For Kubernetes RBAC auditing, our [rakkess vs kubiscan vs RBAC Manager guide](../2026-05-17-self-hosted-kubernetes-rbac-auditing-rakkess-vs-kubiscan-vs-rbac-manager-guide/) covers it.

## FAQ

### Is doas a complete replacement for sudo?

For most common use cases, yes. doas supports the core functionality of running commands as another user with configurable permissions and password requirements. However, it lacks some advanced sudo features like command aliases, run-as-group specifications, fine-grained environment variable control, and the extensive plugin ecosystem. If your sudo configuration uses these advanced features, migration requires re-architecting your access policies.

### Can I use sudo and doas together on the same system?

Yes. They are independent tools with separate configuration files. You can install both and use doas for everyday user privilege escalation while keeping sudo available for scripts and automation that depend on its specific behavior. Many administrators migrate gradually by configuring doas first and removing sudo only after verifying all workflows function correctly.

### How does polkit differ from sudo in terms of user experience?

The user experience is fundamentally different. sudo and doas are invoked directly by users in the terminal (`sudo command` or `doas command`). polkit operates in the background — applications request authorization through D-Bus, and polkit decides whether to grant it based on rules. End users typically interact with polkit through GUI authentication dialogs or command-line tools like `pkexec`. For server administration, polkit is not a direct replacement for interactive privilege escalation.

### Which tool has the best auditing capabilities?

sudo provides the most comprehensive auditing, logging every command execution with user identity, timestamp, working directory, and command arguments to syslog or journald. doas provides basic logging of allowed and denied attempts. polkit logs authorization decisions to the journal but requires additional configuration to capture full command context. For compliance requirements (SOC 2, PCI DSS), sudo is the most capable out of the box.

### Is polkit secure for server environments?

polkit is designed primarily for desktop environments, but its server adoption has grown due to systemd integration. The main security consideration is its D-Bus communication model, which has been the source of several local privilege escalation vulnerabilities. However, polkit is actively maintained, and most distributions ship with security-hardened defaults. For server-only environments without systemd-dependent services, sudo or doas may be preferable due to their simpler security models.

### How do I migrate from sudo to doas on an existing server?

The migration process involves: (1) installing doas via your package manager, (2) translating your `/etc/sudoers` rules to `/etc/doas.conf` syntax, (3) testing the configuration with a root shell open, (4) verifying all automated scripts and deployment pipelines work with doas, and (5) removing sudo only after confirming no workflows break. The syntax translation is straightforward for basic rules but may require creative solutions for complex sudoers configurations involving command aliases or environment specifications.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Privilege Escalation Management: sudo vs doas vs polkit",
  "description": "Compare sudo, doas, and polkit for Linux privilege escalation management. Configuration examples, security analysis, and Docker deployment guides for self-hosted server access control.",
  "datePublished": "2026-05-25",
  "dateModified": "2026-05-25",
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
