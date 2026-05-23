---
title: "Self-Hosted Linux Sandboxing Frameworks — Landlock vs Seccomp-BPF vs Bubblewrap"
date: "2026-05-24"
tags: ["linux-security", "sandboxing", "system-hardening", "landlock", "seccomp"]
draft: false
---

Linux sandboxing frameworks provide essential isolation layers for running untrusted workloads on self-hosted servers. This guide compares three major approaches: **Landlock** (the kernel LSM for filesystem sandboxing), **Seccomp-BPF** (system call filtering), and **Bubblewrap** (user-space sandboxing). Each offers different trade-offs between security guarantees, ease of configuration, and performance overhead.

## What Is Linux Sandboxing?

Sandboxing restricts what a process can do — which files it can access, which system calls it can invoke, and which kernel resources it can manipulate. On self-hosted servers running multiple services, sandboxing prevents a compromised application from affecting other services or the host system.

The Linux kernel provides multiple sandboxing mechanisms at different levels:

- **Mandatory Access Control (MAC)** — Kernel-level enforcement via LSM hooks (Landlock, AppArmor, SELinux)
- **System call filtering** — Restricts which syscalls a process can invoke (Seccomp-BPF)
- **User-space isolation** — Combines namespaces, capabilities, and filesystem mounts (Bubblewrap)

Understanding the differences between these approaches helps you choose the right tool for each workload.

## Landlock: Filesystem Sandbox LSM

**GitHub**: kernel source (built into Linux 5.13+) | **Stars**: N/A (in-tree)

Landlock is a Linux Security Module (LSM) introduced in kernel 5.13 that enables unprivileged processes to restrict their own filesystem access. Unlike AppArmor or SELinux, which require root configuration, Landlock allows any process to define its own sandbox rules.

### Key Features

- **Unprivileged sandboxing** — No root access needed to set up rules
- **Filesystem-focused** — Controls file read, write, execute, and directory traversal
- **Inheritance** — Rules are inherited by child processes automatically
- **No policy language** — Rules are set via `prctl()` and `landlock_create_ruleset()` syscalls

### How Landlock Works

Landlock uses a ruleset-based approach. A process creates a ruleset, adds access rules for specific file paths, then applies the ruleset to itself:

```c
#include <linux/landlock.h>
#include <sys/prctl.h>
#include <sys/syscall.h>

int ruleset_fd = syscall(SYS_landlock_create_ruleset, NULL, 0, 0);

struct landlock_path_beneath_attr path_beneath = {
    .allowed_access = LANDLOCK_ACCESS_FS_EXECUTE |
                      LANDLOCK_ACCESS_FS_READ_FILE |
                      LANDLOCK_ACCESS_FS_READ_DIR,
    .parent_fd = open("/usr", O_PATH | O_CLOEXEC),
};

syscall(SYS_landlock_add_rule, ruleset_fd, LANDLOCK_RULE_PATH_BENEATH, &path_beneath);
prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0);
syscall(SYS_landlock_restrict_self, ruleset_fd, 0);
```

### Docker Compose Example

Running a service with Landlock requires kernel 5.13+ and a container runtime that supports Landlock passthrough:

```yaml
version: "3.8"
services:
  sandboxed-app:
    image: alpine:latest
    security_opt:
      - seccomp:unconfined  # Landlock handles access control
    volumes:
      - ./data:/app/data:ro
    command: >
      sh -c "
        # Apply Landlock rules from within the container
        python3 /app/setup_landlock.py &&
        exec /app/server
      "
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### Landlock Access Rights

| Access Right | Description | Kernel Version |
|---|---|---|
| `LANDLOCK_ACCESS_FS_EXECUTE` | Execute a file | 5.13+ |
| `LANDLOCK_ACCESS_FS_WRITE_FILE` | Write to a file | 5.13+ |
| `LANDLOCK_ACCESS_FS_READ_FILE` | Read from a file | 5.13+ |
| `LANDLOCK_ACCESS_FS_READ_DIR` | List directory contents | 5.13+ |
| `LANDLOCK_ACCESS_FS_REMOVE_DIR` | Remove a directory | 5.13+ |
| `LANDLOCK_ACCESS_FS_REMOVE_FILE` | Remove a file | 5.13+ |
| `LANDLOCK_ACCESS_FS_MAKE_CHAR` | Create character device | 5.13+ |
| `LANDLOCK_ACCESS_FS_MAKE_DIR` | Create a directory | 5.13+ |
| `LANDLOCK_ACCESS_FS_REFER` | Rename/hardlink files | 5.13+ |
| `LANDLOCK_ACCESS_FS_TRUNCATE` | Truncate a file | 5.13+ |

## Seccomp-BPF: System Call Filtering

**GitHub**: kernel source (built into Linux 3.17+) | **Stars**: N/A (in-tree)

Seccomp (Secure Computing Mode) with BPF (Berkeley Packet Filter) filtering restricts which system calls a process can make. It is the foundation of container sandboxing and is used by Docker, Kubernetes, and systemd by default.

### Key Features

- **Syscall-level control** — Filter individual system calls
- **BPF filtering** — Apply complex rules based on syscall arguments
- **Container default** — Docker uses a default seccomp profile
- **Whitelist/blacklist** — Either allow only specific syscalls or block specific ones

### Seccomp Profile Example

A Docker seccomp profile in JSON format:

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "archMap": [
    {
      "architecture": "SCMP_ARCH_X86_64",
      "subArchitectures": ["SCMP_ARCH_X86", "SCMP_ARCH_X32"]
    }
  ],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "alarm", "bind", "brk",
        "capget", "capset", "chdir", "chmod", "chown", "chown32",
        "clock_getres", "clock_gettime", "clock_nanosleep", "clone",
        "close", "connect", "copy_file_range", "creat", "dup",
        "dup2", "dup3", "epoll_create", "epoll_create1", "epoll_ctl",
        "epoll_ctl_old", "epoll_pwait", "epoll_wait", "epoll_wait_old",
        "eventfd", "eventfd2", "execve", "execveat", "exit", "exit_group"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

### Docker Compose with Seccomp

```yaml
version: "3.8"
services:
  seccomed-app:
    image: nginx:alpine
    security_opt:
      - seccomp:/etc/docker/seccomp/profiles/nginx.json
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache/nginx
      - /var/run
    ports:
      - "8080:80"
```

### Common Seccomp Actions

| Action | Behavior | Use Case |
|---|---|---|
| `SCMP_ACT_ALLOW` | Permit the syscall | Whitelisted operations |
| `SCMP_ACT_ERRNO` | Return error (errno) | Graceful denial |
| `SCMP_ACT_KILL` | Kill the process | Dangerous syscalls |
| `SCMP_ACT_TRAP` | Send SIGSYS signal | Debug/diagnostic |
| `SCMP_ACT_LOG` | Allow but log | Audit mode |

## Bubblewrap: User-Space Sandbox

**GitHub**: https://github.com/containers/bubblewrap | **Stars**: 3,100+

Bubblewrap (bwrap) is a user-space sandboxing tool that combines Linux namespaces, capabilities, and filesystem mounts to create isolated environments. Unlike Landlock and Seccomp, which are kernel-level mechanisms, Bubblewrap operates entirely in user space.

### Key Features

- **No root required** — Uses unprivileged user namespaces
- **Full isolation** — Combines PID, network, mount, and IPC namespaces
- **Filesystem virtualization** — Bind mounts, tmpfs overlays, read-only roots
- **Flatpak foundation** — Powers Flatpak application sandboxing

### Installation

```bash
# Debian/Ubuntu
sudo apt install bubblewrap

# RHEL/CentOS/Fedora
sudo dnf install bubblewrap

# Arch Linux
sudo pacman -S bubblewrap
```

### Basic Usage

```bash
# Run a command in an isolated filesystem namespace
bwrap   --ro-bind /usr /usr   --ro-bind /etc /etc   --dir /tmp   --dir /var   --proc /proc   --dev /dev   --unshare-all   --share-net   /bin/bash

# Run with specific allowed paths
bwrap   --ro-bind /usr /usr   --ro-bind /etc /etc   --bind ~/data /data   --dir /tmp   --proc /proc   --dev /dev   --unshare-pid   --unshare-user   --unshare-ipc   --unshare-mount   /bin/bash
```

### Docker Compose with Bubblewrap

```yaml
version: "3.8"
services:
  bwrap-app:
    image: ubuntu:22.04
    security_opt:
      - apparmor:unconfined
      - seccomp:unconfined
    volumes:
      - ./app:/app:ro
      - ./data:/data
    command: >
      bwrap
      --ro-bind /usr /usr
      --ro-bind /etc /etc
      --bind /data /data
      --dir /tmp
      --proc /proc
      --dev /dev
      --unshare-all
      --share-net
      /app/start.sh
    read_only: true
    tmpfs:
      - /tmp
```

## Comparison: Landlock vs Seccomp-BPF vs Bubblewrap

| Feature | Landlock | Seccomp-BPF | Bubblewrap |
|---|---|---|---|
| **Layer** | Kernel LSM | Kernel syscall filter | User-space tool |
| **Primary Scope** | Filesystem access | System call filtering | Full namespace isolation |
| **Requires Root** | No | No (for profile creation) | No (unprivileged namespaces) |
| **Kernel Version** | 5.13+ | 3.17+ | Any (user-space) |
| **Container Support** | Limited (needs runtime support) | Native (Docker default) | Yes (with namespace support) |
| **Performance Overhead** | Minimal | Minimal | Low (namespace setup) |
| **Configuration** | C API / liblandlock | JSON profile | CLI arguments |
| **Child Inheritance** | Automatic | Automatic | Per-process |
| **Network Isolation** | No | No | Yes (--unshare-net) |
| **Best For** | Untrusted file processing | Container syscall hardening | Application sandboxing |

## Combining Sandboxing Layers

The strongest security comes from combining multiple sandboxing mechanisms:

```bash
# Example: Bubblewrap + Seccomp + Landlock
# 1. Use Bubblewrap for namespace isolation
# 2. Apply Seccomp to restrict syscalls
# 3. Use Landlock for fine-grained filesystem access

bwrap   --ro-bind /usr /usr   --ro-bind /etc /etc   --dir /tmp   --proc /proc   --dev /dev   --unshare-all   --share-net   --seccomp 3<seccomp-profile.json   /app/sandboxed-process
```

In practice, Docker already combines Seccomp with AppArmor/SELinux. Adding Landlock provides an additional filesystem-level restriction layer that works independently of the other mechanisms.

## Why Self-Host Sandboxing Frameworks?

Self-hosted applications often process untrusted data — user uploads, API requests, third-party webhooks. Without sandboxing, a vulnerability in any service can compromise the entire server. Sandboxing frameworks provide defense-in-depth:

**Containment of compromised services** — If a web application is exploited, sandboxing limits the attacker's ability to read `/etc/shadow`, access other services' data, or pivot to the host system.

**Multi-tenant isolation** — Self-hosted platforms serving multiple users or organizations benefit from per-tenant sandboxing, ensuring that one tenant's compromised service cannot access another's data.

**Compliance and auditing** — Many security standards (SOC 2, ISO 27001) require process isolation and least-privilege execution. Sandboxing frameworks provide measurable controls for audit purposes.

**Reduced blast radius** — Even with perfect application security, vulnerabilities in dependencies (Log4Shell, etc.) are inevitable. Sandboxing ensures that a single compromised container has minimal impact on the broader infrastructure.

For container security scanning, see our [container image analysis guide](../2026-05-24-self-hosted-container-image-analysis-tools-dive-skopeo-crane-guide/). For kernel-level filesystem security, our [native filesystem encryption comparison](../2026-05-23-self-hosted-linux-native-filesystem-encryption-fscrypt-vs-ecryptfs-vs-dm-crypt/) covers complementary protections.

## FAQ

### What is the difference between Landlock and Seccomp?

Landlock restricts **filesystem access** at the LSM level, controlling which files and directories a process can read, write, or execute. Seccomp restricts **system calls**, controlling which kernel functions a process can invoke. They operate at different layers and are complementary — Landlock controls *what files* you can access, while Seccomp controls *what kernel operations* you can perform.

### Can I use Landlock without root access?

Yes. Landlock is specifically designed for unprivileged sandboxing. Any process can create a Landlock ruleset and apply it to itself using `prctl(PR_SET_NO_NEW_PRIVS, 1)` followed by `landlock_restrict_self()`. This makes Landlock ideal for sandboxing user applications without requiring administrative privileges.

### Does Docker support Landlock?

Docker does not natively support Landlock ruleset configuration as of 2026. However, Landlock rules can be applied from within a container, and container runtimes like containerd and CRI-O have experimental Landlock support. For now, Seccomp remains the primary sandboxing mechanism in Docker.

### Is Bubblewrap as secure as kernel-level sandboxing?

Bubblewrap uses the same kernel mechanisms (namespaces, capabilities) as Docker and other container runtimes, so its isolation is kernel-enforced. However, because it operates in user space, the configuration is more flexible and easier to audit. The security boundary is the same kernel — the difference is in how the isolation is set up and managed.

### Which sandboxing approach should I use for my self-hosted services?

For **containers**, use Docker's default Seccomp profile plus a custom profile for your specific service. For **user-space applications** that need filesystem isolation, use Bubblewrap. For **fine-grained filesystem access control** within an application, use Landlock. The best approach combines all three: namespaces for isolation, Seccomp for syscall filtering, and Landlock for filesystem restrictions.

### Does sandboxing affect performance?

The performance overhead of all three mechanisms is minimal. Landlock adds approximately 1-2% overhead to filesystem operations. Seccomp-BPF filtering adds less than 1% overhead per syscall. Bubblewrap's namespace setup has a one-time cost during process startup but no ongoing runtime overhead. For most self-hosted workloads, sandboxing does not measurably impact performance.

### Can I combine Landlock and Seccomp in the same process?

Yes, and this is the recommended approach. Seccomp restricts which syscalls the process can make, and Landlock restricts which files the process can access through those allowed syscalls. Together, they provide defense-in-depth: even if a Seccomp rule is too permissive, Landlock provides an additional filesystem-level barrier.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Sandboxing Frameworks — Landlock vs Seccomp-BPF vs Bubblewrap",
  "description": "Comprehensive comparison of Linux sandboxing frameworks: Landlock (filesystem LSM), Seccomp-BPF (syscall filtering), and Bubblewrap (user-space isolation) for self-hosted server security.",
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
