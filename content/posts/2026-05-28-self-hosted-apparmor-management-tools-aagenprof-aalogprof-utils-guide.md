---
title: "Self-Hosted AppArmor Management Tools — aa-genprof vs aa-logprof vs AppArmor Utils"
date: "2026-05-28"
tags: ["apparmor", "security", "mandatory-access-control", "linux-security", "self-hosted", "hardening"]
draft: false
---

AppArmor is a Linux Security Module (LSM) that implements mandatory access control (MAC) through per-program profiles. Unlike SELinux, which uses a centralized policy language, AppArmor attaches security profiles directly to executable paths, making it more intuitive for system administrators. However, writing and managing AppArmor profiles manually is complex. Several tools simplify profile creation, enforcement, and auditing.

## Understanding AppArmor

AppArmor works by intercepting system calls and comparing them against per-program profiles. These profiles define which files, network sockets, and capabilities a program can access. Programs run in one of three modes:

- **Enforce** — policy violations are blocked and logged
- **Complain** — violations are logged but not blocked (learning mode)
- **Kill** — program is immediately terminated on violation

The challenge is writing correct profiles: too permissive and you get no protection; too restrictive and you break application functionality. Management tools help bridge this gap.

## aa-genprof (AppArmor Profile Generator)

`aa-genprof` is the standard AppArmor profile generation tool, included in the `apparmor-utils` package. It runs a program in complain mode, monitors log entries for denied accesses, and interactively guides you through creating a profile.

**Key features:**
- Interactive profile creation guided by actual program behavior
- Real-time log monitoring for denied accesses
- Automatic permission suggestions based on access patterns
- Support for file, network, and capability rules
- Profile refinement through iterative test cycles
- Included in all AppArmor distributions (Ubuntu, SUSE, Debian)

### Installation and Usage

```bash
# Install AppArmor utilities
apt install apparmor-utils

# Generate a profile for a new application
aa-genprof /usr/bin/myapp

# This will:
# 1. Set the program to complain mode
# 2. Start the program
# 3. Monitor /var/log/syslog for denied accesses
# 4. Prompt you to allow/deny each access
# 5. Write the profile to /etc/apparmor.d/
```

### Docker Compose Deployment

AppArmor tools run on the host system, not in containers. However, you can deploy an AppArmor management container that communicates with the host's AppArmor daemon:

```yaml
version: "3.8"
services:
  apparmor-manager:
    image: ubuntu:latest
    container_name: apparmor-manager
    privileged: true
    volumes:
      - /etc/apparmor.d:/etc/apparmor.d
      - /var/log:/var/log:ro
      - /sys/kernel/security:/sys/kernel/security
    command: >
      bash -c "
        apt update && apt install -y apparmor-utils &&
        tail -f /var/log/syslog
      "
    restart: unless-stopped
```

### GitHub Stats
- **Package:** apparmor-utils (part of AppArmor project)
- **Project Stars:** 1,590+
- **URL:** [gitlab.com/apparmor/apparmor](https://gitlab.com/apparmor/apparmor)

## aa-logprof (AppArmor Log Profiler)

`aa-logprof` is complementary to `aa-genprof`. While `aa-genprof` creates new profiles, `aa-logprof` updates existing profiles based on new denial events in the system logs. This is essential for maintaining profiles as applications evolve.

**Key features:**
- Updates existing profiles based on recent denial events
- Handles profile changes after application updates
- Supports bulk processing of log entries
- Interactive permission granting/denying
- Profile diff display before applying changes
- Works with both complain and enforce mode logs

### Typical Workflow

```bash
# After updating an application, check for new denials
aa-logprof

# Review and update the profile
# aa-logprof reads /var/log/syslog for apparmor DENIED entries
# Prompts for each new access pattern:
#   [1 - /etc/myapp/config read]
#     Severity: 3
#     [/usr/bin/myapp] /etc/myapp/config r
#   Allow / Deny / Glob / Glob-with-regex / Quit / Help
```

### Profile Location

```bash
# All profiles are stored in /etc/apparmor.d/
ls /etc/apparmor.d/
# usr.bin.nginx
# usr.sbin.mysqld
# docker-default
# ...

# Check status of all profiles
aa-status
# 45 profiles are loaded.
# 45 profiles are in enforce mode.
# 0 profiles are in complain mode.

# Toggle a profile between modes
aa-enforce /etc/apparmor.d/usr.bin.myapp
aa-complain /etc/apparmor.d/usr.bin.myapp
```

## AppArmor Utilities (apparmor-utils Package)

The `apparmor-utils` package provides a comprehensive suite of command-line tools for managing AppArmor profiles beyond just generation and log processing.

**Key tools included:**
- `aa-status` — display loaded profiles and their modes
- `aa-enforce` — switch profiles to enforce mode
- `aa-complain` — switch profiles to complain mode
- `aa-disable` — disable a profile entirely
- `aa-audit` — enable audit mode for a profile
- `aa-autodep` — create a basic profile from scratch
- `aa-remove-unknown` — remove unknown/unloaded profiles
- `aa-teardown` — unload all AppArmor profiles
- `apparmor_parser` — compile and load profiles into the kernel
- `aa-notify` — desktop notification for AppArmor events

### Batch Profile Management

```bash
# Switch ALL profiles to enforce mode
aa-enforce /etc/apparmor.d/*

# Switch ALL profiles to complain mode (for testing)
aa-complain /etc/apparmor.d/*

# Disable a specific profile
aa-disable /etc/apparmor.d/usr.bin.myapp

# Check which profiles are loaded and their modes
aa-status --json

# Reload all profiles after editing
systemctl reload apparmor
```

### GitHub Stats
- **Project:** AppArmor (apparmor-utils is part of the project)
- **Stars:** 1,590+ (GitLab)
- **URL:** [gitlab.com/apparmor/apparmor](https://gitlab.com/apparmor/apparmor)

## Feature Comparison

| Feature | aa-genprof | aa-logprof | apparmor-utils |
|---------|-----------|------------|----------------|
| Profile Creation | Interactive | Update existing | Basic auto-gen |
| Log Analysis | Real-time | Batch processing | Status only |
| Mode Management | No | No | Full suite |
| Profile Editing | Interactive | Interactive | Manual/CLI |
| Bulk Operations | No | No | Yes |
| JSON Output | No | No | aa-status --json |
| Desktop Notifications | No | No | aa-notify |
| Kernel Integration | Direct | Direct | Direct |
| Learning Mode | Yes (gen) | Yes (update) | No |

## Profile Writing Best Practices

### Minimal Permission Principle

```apparmor
# Good: Specific file permissions
/usr/bin/myapp {
  # Only allow reading specific config files
  /etc/myapp/*.conf r,
  /etc/myapp/certs/ rw,

  # Only allow writing to log directory
  /var/log/myapp/ w,
  /var/log/myapp/*.log rw,

  # Network: only allow TCP outbound on port 443
  network inet tcp,
  network inet6 tcp,

  # Capabilities: minimal set
  capability dac_override,
}

# Bad: Overly permissive
/usr/bin/myapp {
  /** rw,
  network,
  capability,
}
```

### Using Abstractions

```apparmor
#include <tunables/global>

/usr/bin/nginx {
  # Use built-in abstractions for common patterns
  #include <abstractions/base>
  #include <abstractions/nameservice>
  #include <abstractions/ssl_certs>
  #include <abstractions/apache2-common>

  # Program-specific rules
  /etc/nginx/ r,
  /etc/nginx/** r,
  /var/www/** r,
  /var/log/nginx/ rw,
  /var/log/nginx/*.log rw,
}
```

## Deployment Architecture

```
┌────────────────────────────────────────────────────┐
│              AppArmor Kernel Module                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ Profile 1│  │ Profile 2│  │ Profile N│         │
│  │(enforce) │  │(complain)│  │(enforce) │         │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘         │
└───────┼─────────────┼─────────────┼────────────────┘
        │             │             │
┌───────▼─────────────▼─────────────▼────────────────┐
│           AppArmor Userspace Tools                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │ aa-genprof│ │ aa-logprof│ │aa-status │         │
│  │(generate)│ │ (update) │ │(monitor) │         │
│  └──────────┘  └──────────┘  └──────────┘         │
└────────────────────────────────────────────────────┘
```

## Choosing the Right Tool

**Use aa-genprof** when:
- Creating a profile for a new application from scratch
- You want interactive guidance based on actual program behavior
- You need to understand what resources a program accesses

**Use aa-logprof** when:
- Updating an existing profile after application changes
- Reviewing denial events from complain mode
- Fine-tuning profiles that are too restrictive

**Use apparmor-utils CLI** when:
- Performing bulk mode changes across multiple profiles
- Monitoring profile status and loaded rules
- Automating AppArmor management in scripts
- Enabling audit mode for compliance logging

For broader Linux security topics, see our [server security auditing guide](../2026-04-26-lynis-vs-openscap-vs-goss-self-hosted-server-security-auditing-guide/) and [file integrity monitoring comparison](../self-hosted-file-integrity-monitoring-aide-ossec-tripwire-guide-2026/).

## Security Considerations

1. **Start in complain mode** — Always test new profiles in complain mode before switching to enforce
2. **Monitor denial logs** — Regular review of `/var/log/syslog` for AppArmor DENIED entries catches misconfigurations
3. **Version-control profiles** — Store AppArmor profiles in Git for change tracking and rollback
4. **Audit regularly** — Run `aa-status` periodically to verify all expected profiles are loaded
5. **Test after updates** — Application updates often change file access patterns; re-run `aa-logprof` after updates
6. **Use include abstractions** — Leverage AppArmor's built-in abstractions for common permission patterns
7. **Avoid wildcard overuse** — `/**` permissions defeat the purpose of mandatory access control

## Why Self-Host AppArmor Management?

Implementing mandatory access control through AppArmor adds a critical defense layer that complements traditional discretionary access control. Understanding why organizations invest in AppArmor profile management reveals the broader value proposition of self-hosted Linux security hardening.

### Defense in Depth
AppArmor provides process-level isolation that limits the blast radius of a compromised application. Even if an attacker exploits a vulnerability in nginx or MySQL, AppArmor profiles restrict what the compromised process can access — files, network connections, and system capabilities are all constrained by the profile. This is especially valuable for internet-facing services.

### Compliance Requirements
Many regulatory frameworks (PCI DSS, HIPAA, SOX) require mandatory access control or equivalent process isolation mechanisms. AppArmor profiles provide auditable, documented security policies that satisfy these requirements without the complexity of SELinux policy language.

For organizations managing multiple security layers, AppArmor complements other hardening tools. See our [server management dashboard comparison](../2026-04-27-cockpit-vs-webmin-vs-ajenti-self-hosted-server-management-web-ui/) for broader infrastructure security management.

### Cost-Free Enterprise Security
Enterprise Linux security platforms like Red Hat Satellite, SUSE Manager, or Qualys Vulnerability Management can cost thousands per node annually. AppArmor is included free with Ubuntu, SUSE, and Debian — providing comparable mandatory access control without licensing costs. For a fleet of 100 servers, the savings exceed $50,000 annually.

### Application-Specific Hardening
Unlike firewall rules that operate at the network level, AppArmor profiles protect at the application level. You can create different profiles for different services on the same machine, each with precisely scoped permissions. This granularity is impossible to achieve with traditional Linux permissions alone.

## FAQ

### What is the difference between AppArmor and SELinux?
AppArmor uses path-based profiles attached to executables, making it simpler to understand and manage. SELinux uses label-based policies with a more expressive but complex policy language. AppArmor is generally preferred for its ease of use; SELinux for its flexibility.

### Can I use AppArmor and SELinux together?
No. The Linux kernel only supports one LSM at a time. You must choose either AppArmor or SELinux (or another LSM like TOMOYO or Smack).

### How do I troubleshoot a broken AppArmor profile?
Switch the profile to complain mode (`aa-complain`), reproduce the issue, then run `aa-logprof` to review denial events and update the profile. Check `/var/log/syslog` for AppArmor DENIED messages.

### Does AppArmor work with Docker containers?
Yes. AppArmor profiles can be applied to Docker containers using the `--security-opt apparmor=profile_name` flag. Docker also ships with a default AppArmor profile (`docker-default`).

### How often should I review AppArmor profiles?
After every application update, as updates may change file access patterns. Additionally, quarterly reviews of complain mode profiles help identify profiles that should be moved to enforce mode.

### Can I write AppArmor profiles manually?
Yes. Profile files are plain text stored in `/etc/apparmor.d/`. Use `apparmor_parser` to compile and load them. However, `aa-genprof` is recommended for initial creation as it captures actual access patterns.

### Does AppArmor impact performance?
Minimal. AppArmor's kernel-level filtering adds negligible overhead (typically < 1% CPU). The primary performance consideration is the initial profile creation process, not runtime enforcement.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted AppArmor Management Tools — aa-genprof vs aa-logprof vs AppArmor Utils",
  "description": "Compare self-hosted AppArmor management tools: aa-genprof, aa-logprof, and apparmor-utils. Profile creation, enforcement, and security hardening for Linux.",
  "datePublished": "2026-05-28",
  "dateModified": "2026-05-28",
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
