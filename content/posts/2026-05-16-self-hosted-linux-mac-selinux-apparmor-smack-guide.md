---
title: "Self-Hosted Linux Mandatory Access Control: SELinux vs AppArmor vs SMACK (2026)"
date: "2026-05-16"
tags: ["security", "linux", "selinux", "apparmor", "mac", "access-control", "hardening"]
draft: false
description: "Compare SELinux, AppArmor, and SMACK for mandatory access control on self-hosted Linux servers. Complete guide with policy management, Docker configurations, and security best practices."
---

Mandatory Access Control (MAC) is the most powerful security mechanism available on Linux. Unlike Discretionary Access Control (DAC), where file owners decide who gets access, MAC enforces system-wide security policies that even root cannot bypass. For self-hosted servers running critical infrastructure — web applications, databases, mail servers, and container workloads — implementing a MAC framework is essential defense-in-depth.

Three major MAC frameworks dominate the Linux security landscape: **SELinux**, **AppArmor**, and **SMACK**. Each takes a fundamentally different approach to restricting process behavior, and choosing the right one depends on your security requirements, distribution, and operational complexity tolerance.

This guide compares all three frameworks, provides deployment configurations, and helps you decide which MAC system best protects your self-hosted infrastructure.

## What Is Mandatory Access Control?

Traditional Linux security relies on DAC — file permissions, ownership, and group memberships. If a process runs as root, it can access any file, open any network socket, and execute any system call. A compromised service with elevated privileges becomes a gateway to total system compromise.

MAC frameworks add an additional enforcement layer that operates independently of user identity. Every process and resource is assigned a security label, and the kernel checks policy rules before granting access. Even if an attacker gains root access through a service exploit, the MAC policy limits what they can do — reading sensitive files, spawning reverse shells, or escalating to other services.

| Feature | SELinux | AppArmor | SMACK |
|---------|---------|----------|-------|
| **Developer** | NSA / Red Hat | Novell / SUSE | Casey Schaufler |
| **Access Model** | Type Enforcement (MCS/MLS) | Path-based profiles | Label-based rules |
| **Policy Language** | M4 macros + CIL | Simplified profile syntax | Simple label rules |
| **Default Distro** | RHEL, Fedora, CentOS | Ubuntu, Debian, SUSE | Tizen, embedded Linux |
| **Learning Curve** | Steep | Moderate | Low |
| **Granularity** | Very fine-grained | File/path-level | Object-level labels |
| **GitHub Stars** | 1,589+ (userland) | Kernel-integrated | Kernel-integrated |
| **Container Support** | Full (container-selinux) | Full (snap/AppArmor) | Limited |

## SELinux: Type Enforcement at Scale

SELinux (Security Enhanced Linux) implements Type Enforcement, the most granular MAC model available on Linux. Every process runs in a specific domain (type), and every file, port, and device has a type label. Policies define which domains can interact with which types — and through which operations.

SELinux ships enabled by default on RHEL, Fedora, CentOS, and AlmaLinux. Its policy language supports Multi-Category Security (MCS) and Multi-Level Security (MLS), making it suitable for both commercial servers and government-grade deployments.

### Key Advantages

- **Finest granularity**: Controls access at the syscall level with type transitions
- **Mature ecosystem**: 20+ years of development, extensive policy modules
- **Container-native**: Built-in container policy (`container_t`, `container_runtime_t`)
- **MLS/MCS support**: Multi-level security for classified environments
- **Active development**: SELinuxProject userland repo at 1,589+ stars, kernel integration maintained by NSA

### Docker Compose: SELinux-Enabled Container Deployment

```yaml
version: "3.8"
services:
  webapp:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html:Z
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro,Z
    security_opt:
      - label=level:s0:c100,c200
      - label=type:container_t
    restart: unless-stopped

  database:
    image: postgres:16-alpine
    volumes:
      - pgdata:/var/lib/postgresql/data:Z
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    security_opt:
      - label=level:s0:c100
      - label=type:container_t
    restart: unless-stopped

volumes:
  pgdata:
    driver: local
```

The `:Z` flag relabels volume content with a unique MCS category, preventing containers from accessing each other's data even if both are compromised.

### Managing SELinux Policies

```bash
# Check current mode
getenforce

# Set to enforcing (persistent)
setenforce 1

# Find denied access attempts
ausearch -m avc -ts recent | audit2why

# Generate policy module from denials
ausearch -m avc -ts recent | audit2allow -M myapp

# Install generated module
semodule -i myapp.pp

# List all loaded modules
semodule -l

# Check file contexts
ls -lZ /var/www/html/

# Restore default contexts
restorecon -Rv /var/www/html/
```

## AppArmor: Path-Based Simplicity

AppArmor takes a fundamentally different approach. Instead of type labels, it uses file paths to define what each application can access. Each application has a profile that specifies allowed file reads/writes, network access, capabilities, and signal permissions.

AppArmor is the default MAC on Ubuntu, Debian, and openSUSE. It ships with hundreds of pre-built profiles for common applications, making it much easier to adopt than SELinux for most administrators.

### Key Advantages

- **Lower learning curve**: Path-based rules are intuitive and readable
- **Pre-built profiles**: Apparmor-utils includes profiles for Apache, Nginx, MySQL, and more
- **Easy debugging**: complain mode logs violations without blocking
- **Docker integration**: `--security-opt apparmor=` flag for per-container profiles
- **Snap ecosystem**: All Snap packages run under AppArmor confinement

### Docker Compose: AppArmor-Protected Services

```yaml
version: "3.8"
services:
  webapp:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
    security_opt:
      - apparmor=docker-nginx
    restart: unless-stopped

  apparmor-generator:
    image: ubuntu:24.04
    command: >
      bash -c "
      apt-get update && apt-get install -y apparmor-utils &&
      aa-genprofile docker-nginx
      "
    privileged: true
    volumes:
      - /etc/apparmor.d:/etc/apparmor.d
    restart: "no"
```

### Managing AppArmor Profiles

```bash
# Check AppArmor status
sudo aa-status

# List loaded profiles and modes
sudo aa-status --json

# Put profile in complain mode (log only)
sudo aa-complain /etc/apparmor.d/usr.sbin.nginx

# Put profile in enforce mode (block violations)
sudo aa-enforce /etc/apparmor.d/usr.sbin.nginx

# Generate a new profile by tracing application
sudo aa-genprofile /usr/sbin/nginx

# Parse audit logs for violations
sudo aureport -a --summary

# Disable a profile
sudo ln -s /etc/apparmor.d/usr.sbin.nginx /etc/apparmor.d/disable/
sudo apparmor_parser -R /etc/apparmor.d/usr.sbin.nginx
```

## SMACK: Simplified Mandatory Access Control

SMACK (Simplified Mandatory Access Control Kernel) was designed as a lightweight alternative to SELinux. Instead of complex type enforcement or path-based profiles, SMACK assigns a single label to every process and object. Access rules define which labels can read, write, execute, or transmit to other labels.

SMACK is the default security module on Tizen and several embedded Linux distributions. Its simplicity makes it ideal for resource-constrained environments where SELinux's policy complexity is unnecessary.

### Key Advantages

- **Simplest model**: Single labels per object, straightforward access matrix
- **Low overhead**: Minimal performance impact, suitable for embedded systems
- **Easy to understand**: Rules are human-readable without training
- **Kernel-integrated**: No userspace daemon required
- **Upstream maintained**: cschaufler/smack-next repo with active development

### SMACK Rule Management

```bash
# View current SMACK rules
cat /sys/fs/smackfs/onlyrule

# Load SMACK rules
cat << EOF > /etc/smack/rules
# Subject Object Access
_       _       rwxat
User    System  r
System  User    w
WebApp  Database r
WebApp  Network  w
EOF
cp /etc/smack/rules /sys/fs/smackfs/load2

# Set process label
echo "WebApp" > /proc/$$/attr/current

# Set file label
chsmack -a "Database" /var/lib/db/data

# View file label
chsmack /var/lib/db/data

# Set network interface label
echo "Network" > /sys/fs/smackfs/netlabel
```

## Choosing the Right MAC Framework

The decision between SELinux, AppArmor, and SMACK depends on your environment:

| Scenario | Recommended | Reason |
|----------|-------------|--------|
| RHEL/CentOS/Fedora servers | SELinux | Default, mature policies, best tooling |
| Ubuntu/Debian servers | AppArmor | Default, easier management, good profiles |
| Container-heavy workloads | SELinux | Best container isolation with MCS labels |
| Embedded/IoT devices | SMACK | Minimal overhead, simple configuration |
| Compliance (FedRAMP, STIG) | SELinux | Only MAC with MLS certification |
| Quick security hardening | AppArmor | Complain mode, pre-built profiles |
| Multi-tenant hosting | SELinux | Finest isolation between tenants |
| Developer workstations | AppArmor | Lower learning curve, less friction |

## Why Self-Host Your MAC Policy?

Running MAC frameworks on self-hosted servers provides security controls that cloud providers cannot offer. In multi-tenant cloud environments, the hypervisor isolates VMs but cannot enforce application-level access control within your instance. MAC fills this gap by restricting what each process can do regardless of the user identity.

For self-hosted infrastructure — web servers, databases, mail systems, and container orchestration — MAC prevents lateral movement after a service compromise. If your Nginx process is exploited, SELinux or AppArmor prevents the attacker from reading database credentials, accessing SSH keys, or spawning a reverse shell to other services.

For organizations managing compliance requirements (PCI-DSS, SOC 2, HIPAA), MAC enforcement is often mandatory. Self-hosted MAC policies give you full control over security rules without depending on cloud provider security groups or IAM policies.

For related reading on container security layers, see our [container seccomp profile management guide](../2026-05-10-container-seccomp-profile-management-apparmor-firejail-guide/). For broader container runtime security, check our [Falco vs NeuVector vs Tetragon comparison](../2026-04-29-neuvector-vs-falco-vs-tetragon-container-runtime-security-guide/).

## FAQ

### What is the difference between DAC and MAC in Linux?

Discretionary Access Control (DAC) uses file permissions (owner, group, others) to determine access. The file owner can grant or revoke permissions. Mandatory Access Control (MAC) enforces system-wide policies that override user permissions — even root cannot bypass MAC rules. DAC answers "who owns this file?" while MAC answers "is this process allowed to access this resource regardless of ownership?"

### Can I run SELinux and AppArmor at the same time?

No. Linux only supports one Linux Security Module (LSM) for MAC enforcement at a time. You must choose either SELinux, AppArmor, SMACK, or another LSM. However, you can combine MAC with other security mechanisms like seccomp (system call filtering), capabilities (privilege reduction), and namespaces (resource isolation) for defense-in-depth.

### Does AppArmor work on RHEL/CentOS systems?

AppArmor is not the default on RHEL-family distributions and requires kernel module loading that may conflict with SELinux. While technically possible to run AppArmor on RHEL by disabling SELinux, this is not recommended. Use the distribution's default MAC framework — SELinux on RHEL, AppArmor on Ubuntu/Debian — for the best policy coverage and community support.

### How do I debug SELinux policy violations?

Start by checking the audit log: `ausearch -m avc -ts recent`. Use `audit2why` to understand why access was denied. For quick testing, temporarily switch to permissive mode with `setenforce 0` (this logs violations without blocking). Use `audit2allow` to generate policy modules from denial logs. For complex issues, the `sepolicy` tool and SELinux troubleshooting guide provide step-by-step resolution.

### Is SMACK production-ready for server workloads?

SMACK is production-ready for specific use cases — embedded systems, IoT devices, and Tizen-based appliances where simplicity is prioritized over granular policy control. For general-purpose server workloads, SELinux or AppArmor provide more comprehensive policy coverage, better tooling, and wider community support. SMACK's main advantage is operational simplicity, not feature completeness.

### How does MAC protect against container escapes?

MAC frameworks add an enforcement layer between containerized processes and the host kernel. SELinux uses MCS labels to isolate containers from each other — each container gets unique security categories that prevent cross-container file access. AppArmor profiles restrict what syscalls, file paths, and network operations container processes can perform. Combined with seccomp filters and user namespaces, MAC significantly reduces the attack surface of container escape vulnerabilities.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Mandatory Access Control: SELinux vs AppArmor vs SMACK (2026)",
  "description": "Compare SELinux, AppArmor, and SMACK for mandatory access control on self-hosted Linux servers. Complete guide with policy management, Docker configurations, and security best practices.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
