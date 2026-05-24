---
title: "Self-Hosted SELinux Management Tools: semanage vs setools vs audit2allow (2026)"
date: "2026-05-24"
tags: ["selinux", "linux-security", "system-administration", "access-control", "policy-management", "linux"]
draft: false
---

SELinux (Security-Enhanced Linux) is one of the most powerful mandatory access control frameworks available for Linux systems. While the kernel enforces policies, managing those policies effectively requires the right tooling. For self-hosted server administrators, choosing the correct SELinux management tools can mean the difference between a secure, well-tuned system and one that's either locked down too tightly or dangerously permissive.

This guide compares the three primary SELinux management toolsets: **semanage** (policy management), **setools** (policy analysis), and **audit2allow** (exception generation). Each serves a distinct role in the SELinux lifecycle, and understanding when to use each tool is critical for effective security operations.

## Understanding the SELinux Management Ecosystem

SELinux policies define what processes can access which resources. The default targeted policy covers common services, but self-hosted environments often need customizations — new ports, file contexts, boolean toggles, and custom modules. The management ecosystem breaks down into three complementary layers:

- **Policy Management** (semanage): Add, modify, and remove policy elements like ports, users, file contexts, and booleans. This is the day-to-day administrative interface.
- **Policy Analysis** (setools): Inspect, query, and audit existing policies. Understand why access is allowed or denied, trace permission chains, and validate policy correctness.
- **Exception Generation** (audit2allow): Convert denial logs into allow rules. This is the rapid-response tool for getting applications working under SELinux enforcement.

Together, these tools form a complete management workflow: analyze the current policy, identify what needs to change, make the changes, and handle any unexpected denials.

## Tool Comparison at a Glance

| Feature | semanage | setools | audit2allow |
|---------|----------|---------|-------------|
| Primary Purpose | Policy configuration | Policy analysis & auditing | Denial-to-allow conversion |
| Package | policycoreutils-python-utils | setools-console | policycoreutils-python-utils |
| Interactive Mode | No (CLI commands) | Yes (seinfo, sesearch) | No (CLI pipe) |
| Learning Curve | Moderate | Steep | Low |
| Policy Modification | Yes (adds local modifications) | No (read-only analysis) | Yes (generates custom modules) |
| Query Capabilities | Limited (list only) | Extensive (search, analyze) | None |
| Automation Friendly | Yes (scriptable) | Yes (scriptable) | Yes (piped from audit) |
| Best For | Day-to-day administration | Deep policy investigation | Quick exception creation |
| GitHub (upstream) | [SELinuxProject/selinux](https://github.com/SELinuxProject/selinux) (1,592 ★) | [SELinuxProject/setools](https://github.com/SELinuxProject/setools) (195 ★) | [linux-audit/audit-userspace](https://github.com/linux-audit/audit-userspace) (710 ★) |

## semanage: The Day-to-Day Policy Manager

`semanage` is the Swiss Army knife of SELinux administration. It handles virtually all policy element modifications without requiring you to write raw policy source code. When you need to tell SELinux that your web server should listen on port 8443, or that a directory should be treated as web content, `semanage` is the tool.

### Key Subcommands

```bash
# Manage file context mappings
semanage fcontext -a -t httpd_sys_content_t "/srv/webapps(/.*)?"
restorecon -Rv /srv/webapps

# Manage network port definitions
semanage port -a -t http_port_t -p tcp 8443

# Manage SELinux booleans (persistent)
semanage boolean -m --on httpd_can_network_connect

# List current modifications
semanage fcontext -l | grep local
semanage port -l | grep http
semanage boolean -l -C

# Manage SELinux users and roles
semanage user -l
semanage login -a -s staff_u devuser
```

### Docker Deployment

```yaml
services:
  selinux-admin:
    image: alpine:latest
    volumes:
      - /etc/selinux:/etc/selinux:ro
      - /var/lib/selinux:/var/lib/selinux
      - /var/log/audit:/var/log/audit:ro
    command: >
      sh -c "
        apk add policycoreutils policycoreutils-python-utils setools-console
        && semanage fcontext -l
        && semanage port -l
        && sesearch --allow -s httpd_t -t httpd_sys_content_t -c file
      "
    network_mode: host
    restart: no
```

The Docker approach works because `semanage` operates on policy store files, not running kernel state. You can inspect and prepare policy modifications from a container, then apply them on the host.

### When to Use semanage

- Adding custom file contexts for non-standard directory layouts
- Opening non-standard ports for services
- Enabling or disabling SELinux booleans persistently
- Managing SELinux user mappings for multi-user servers
- Any routine policy adjustment that doesn't require custom module compilation

## setools: Deep Policy Analysis and Auditing

Where `semanage` modifies policies, `setools` lets you understand them. The setools suite provides several utilities for querying and analyzing SELinux policy databases. This is essential for troubleshooting, security auditing, and understanding complex permission chains.

### Core Utilities

```bash
# seinfo: Display policy statistics and component listings
seinfo
# Output: Users, roles, types, booleans, rules, etc.

# seinfo --type  # List all types
seinfo --type -x  # With details
seinfo --type httpd_t -x  # Specific type details

# sesearch: Search for allow rules matching criteria
sesearch --allow -s httpd_t -t httpd_sys_content_t -c file
sesearch --allow -s httpd_t -c tcp_socket -p name_connect
sesearch --allow -t shadow_t -p read  # Who can read shadow?

# secheck: Analyze if a specific access is allowed
secheck -s httpd_t -t httpd_sys_content_t -c file -p read

# sedta: Domain Transition Analysis
sedta -s init_t -t httpd_t  # How does init transition to httpd?
```

### Practical Troubleshooting Example

When an application is denied under SELinux, `setools` helps you understand the root cause:

```bash
# Step 1: Find all denials for a service
ausearch -m avc -ts recent --comm nginx | audit2why

# Step 2: Check if the access should theoretically be allowed
sesearch --allow -s httpd_t -t var_log_t -c file -p read

# Step 3: If denied, check what booleans might help
semanage boolean -l | grep httpd

# Step 4: Trace the domain transition path
sedta -s init_t -t httpd_t
```

### When to Use setools

- Troubleshooting SELinux denials when the cause isn't obvious
- Security auditing: "Which domains can access this sensitive file type?"
- Understanding policy complexity before making changes
- Verifying that policy modifications have the expected effect
- Analyzing domain transition paths for security reviews

## audit2allow: Rapid Exception Generation

`audit2allow` converts SELinux denial messages (AVC denials) into allow rules. It's the fastest way to get a custom application working under SELinux when you encounter unexpected denials.

### Basic Workflow

```bash
# Generate allow rules from recent denials
ausearch -m avc -ts recent | audit2allow

# Generate a loadable policy module
ausearch -m avc -ts recent | audit2allow -M mycustom

# Install the module
semodule -i mycustom.pp

# Generate rules for a specific application
grep "comm=\"myapp\"" /var/log/audit/audit.log | audit2allow -M myapp

# Show what WOULD be generated without creating files
ausearch -m avc -ts today | audit2allow -w
```

### Understanding the Output

```
#============= httpd_t ==============
allow httpd_t my_custom_port_t:tcp_socket name_connect;

# Explanation:
# httpd_t needs to connect to my_custom_port_t via TCP
# This is typically safe for web applications connecting to backend services
```

### Safety Considerations

While `audit2allow` is convenient, blindly applying its output can weaken your security posture:

1. **Review every rule** before installing — some denials indicate legitimate security blocks
2. **Use `-w` flag** first to see explanations of what each rule permits
3. **Scope modules narrowly** — create application-specific modules, not catch-all policies
4. **Test in permissive mode** before enforcing with new modules
5. **Audit regularly** — remove rules that are no longer needed

### Docker Compose for Testing

```yaml
services:
  selinux-test:
    image: fedora:latest
    volumes:
      - /var/log/audit:/var/log/audit:ro
      - ./selinux-modules:/etc/selinux/targeted/modules:rw
    command: >
      sh -c "
        dnf install -y policycoreutils-python-utils setools-console audit
        && grep 'denied' /var/log/audit/audit.log | audit2allow -w
        && grep 'denied' /var/log/audit/audit.log | audit2allow -M testmodule
        && semodule -i testmodule.pp
      "
    network_mode: host
```

## Why Self-Host with SELinux Management Tools?

Managing SELinux effectively is crucial for any self-hosted infrastructure. The default targeted policy provides baseline protection, but production environments need customization. Here's why dedicated management tools matter:

**Granular Security Control**: Self-hosted services often run on non-standard ports, use custom file locations, or require network access patterns that the default policy doesn't anticipate. Without proper management tools, administrators either disable SELinux entirely (removing all protection) or leave it in permissive mode (logging but not enforcing).

**Compliance and Auditing**: Many regulatory frameworks require mandatory access controls. Tools like `setools` provide the policy analysis capabilities needed to demonstrate compliance — proving which services can access which resources and under what conditions.

**Operational Efficiency**: The `semanage` command-line interface makes policy changes scriptable and repeatable. For infrastructure managed through configuration management (Ansible, Puppet, Chef), having programmatic access to SELinux policy elements is essential.

For comprehensive file-level encryption strategies, see our [Linux native filesystem encryption guide](../2026-05-23-self-hosted-linux-native-filesystem-encryption-fscrypt-vs-encfs-vs-cryfs-guide/). For container isolation techniques, check our [Linux PID namespace isolation guide](../2026-05-24-self-hosted-linux-pid-namespace-isolation-unshare-bubblewrap-nsenter-guide/).

## Security Best Practices for SELinux Management

1. **Never disable SELinux to fix issues** — use `audit2allow` with review, or adjust booleans via `semanage`
2. **Keep local modifications documented** — run `semanage -l` periodically and record changes
3. **Use setools for security reviews** — before deploying new services, analyze their policy requirements
4. **Test in permissive mode first** — switch to permissive, let the system run for a week, then analyze denials
5. **Minimize custom modules** — prefer boolean toggles and file context changes over custom allow rules
6. **Audit your policy store** — `seinfo | head` gives you a quick complexity metric; track it over time

```bash
# Quick security audit script
#!/bin/bash
echo "=== SELinux Policy Summary ==="
seinfo | head -20

echo "=== Local Modifications ==="
echo "File contexts: $(semanage fcontext -l -C | wc -l)"
echo "Ports: $(semanage port -l -C | wc -l)"
echo "Booleans: $(semanage boolean -l -C | wc -l)"
echo "Modules: $(semodule -l | wc -l)"

echo "=== Current Enforcing Domains ==="
sestatus | grep "Current mode"
```

## Choosing the Right SELinux Management Tool

Your choice depends on the task at hand:

| Scenario | Recommended Tool | Reason |
|----------|-----------------|--------|
| Open a port for a new service | `semanage port -a` | Direct, persistent configuration |
| Figure out why access is denied | `sesearch` + `ausearch` | Deep policy analysis |
| Quick fix for a custom application | `audit2allow -M` | Fast exception generation |
| Security audit of production system | `setools` (seinfo, sesearch) | Read-only analysis |
| Policy documentation | `semanage -l` + `seinfo` | Complete policy listing |
| Automate policy in CI/CD | `semanage` (scriptable) | Programmatic interface |

For most self-hosted administrators, `semanage` handles 80% of daily tasks, `setools` handles deep troubleshooting, and `audit2allow` handles the occasional edge case. All three are part of the standard SELinux userspace tools package and available on any distribution with SELinux support.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted SELinux Management Tools: semanage vs setools vs audit2allow (2026)",
  "description": "Compare SELinux management tools: semanage for policy configuration, setools for policy analysis, and audit2allow for exception generation.",
  "datePublished": "2026-05-24",
  "dateModified": "2026-05-24",
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

## FAQ

### What is the difference between semanage and setools?

`semanage` modifies SELinux policy elements — it adds, changes, or removes ports, file contexts, booleans, and user mappings. `setools` is read-only — it lets you inspect, query, and analyze the current policy to understand what is allowed and why. Think of `semanage` as the configuration tool and `setools` as the diagnostic tool.

### Is it safe to use audit2allow to fix SELinux denials?

`audit2allow` is safe when you review its output first. Always use the `-w` flag to see explanations of what each generated rule permits. Some denials indicate legitimate security blocks (e.g., a compromised process trying to access sensitive files), so blindly applying all generated rules can weaken your security. Best practice: review each rule, create narrow application-specific modules, and test in permissive mode before enforcing.

### How do I make semanage changes persistent across reboots?

All `semanage` changes are persistent by default — they modify the policy store on disk, not the running kernel state. Changes made with `semanage boolean -m`, `semanage fcontext -a`, and `semanage port -a` survive reboots. However, you need to run `restorecon` after file context changes to apply them to existing files.

### Can I manage SELinux from a Docker container?

Yes, you can inspect and prepare SELinux policy modifications from a container by mounting `/etc/selinux`, `/var/lib/selinux`, and `/var/log/audit`. However, applying policy changes (`semodule -i`) requires direct host access since the kernel policy state can only be modified from the host. The container approach is useful for analysis, testing, and preparing changes.

### Which distributions support these SELinux management tools?

These tools are available on all distributions with SELinux support: Fedora, RHEL, CentOS Stream, AlmaLinux, Rocky Linux, and Debian/Ubuntu (with SELinux packages installed). The package names vary slightly — on Fedora/RHEL they're `policycoreutils-python-utils` and `setools-console`, while on Debian/Ubuntu they're `policycoreutils` and `setools`.

### How do I check if SELinux is currently enforcing?

Run `sestatus` or `getenforce`. `sestatus` provides detailed information including the loaded policy name, current mode (enforcing/permissive/disabled), and boolean settings. `getenforce` simply returns the current mode. For scripting, `getenforce | grep -q Enforcing` is a reliable test.

