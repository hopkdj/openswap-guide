---
title: "Self-Hosted Container Seccomp Profile Management: AppArmor vs Seccomp vs Firejail (2026)"
date: "2026-05-10"
tags: ["security", "containers", "seccomp", "apparmor", "sandbox", "linux"]
draft: false
---

Container security extends far beyond image scanning and network isolation. At the kernel level, three complementary security mechanisms — **Seccomp**, **AppArmor**, and **Firejail** — restrict what processes inside containers can actually do. These are not alternatives to each other but rather **defense-in-depth layers** that work together to create a robust container sandbox. Understanding how each mechanism works and how to manage them effectively is critical for running containers securely in production.

This guide explains how to create, manage, and deploy security profiles for containers using the Linux kernel's built-in security frameworks. We compare Seccomp filters, AppArmor profiles, and Firejail sandboxes — three complementary approaches to restricting container process capabilities at the system call, file access, and user-space levels.

## Understanding Container Security Layers

Containers share the host kernel, which means a compromised container process has the same kernel attack surface as any other host process. Linux provides several mechanisms to limit this attack surface:

| Layer | Mechanism | What It Restricts |
|-------|-----------|-------------------|
| **System calls** | Seccomp | Which syscalls a process can invoke |
| **File/Network access** | AppArmor | What files, capabilities, and network operations are permitted |
| **Resource access** | Namespaces + cgroups | Visibility into host resources and resource limits |
| **User-space sandboxing** | Firejail | Application-level restrictions (X11, devices, network) |
| **Kernel isolation** | gVisor/Kata | Separate kernel or microVM for complete isolation |

Seccomp and AppArmor are **kernel-level** mechanisms enforced by Linux itself. Firejail is a **user-space** sandboxing tool that uses namespaces, seccomp, and other kernel features under the hood but provides a simpler, application-oriented interface.

## Seccomp (Secure Computing Mode)

**Seccomp** is a Linux kernel security feature that filters system calls made by a process. When a process enters seccomp mode, the kernel checks each system call against a Berkeley Packet Filter (BPF) program. If the syscall is not allowed, the kernel kills the process or returns an error.

### Key Features

- **Syscall filtering** — whitelist or blacklist specific system calls
- **BPF-based rules** — highly efficient, compiled filter programs
- **Docker integration** — built-in seccomp profiles for containers
- **Fine-grained control** — filter by syscall, arguments, and return values
- **Default deny mode** — only explicitly allowed syscalls pass through

### Default Docker Seccomp Profile

Docker ships with a default seccomp profile that blocks approximately 44 dangerous system calls while allowing the ~300 syscalls that typical applications need. This profile blocks syscalls like `mount`, `umount`, `reboot`, `swapon`, `swapoff`, `ptrace`, and kernel module loading.

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": [
    "SCMP_ARCH_X86_64",
    "SCMP_ARCH_X86",
    "SCMP_ARCH_X32"
  ],
  "syscalls": [
    {
      "names": [
        "accept", "accept4", "access", "alarm", "bind",
        "brk", "capget", "capset", "chdir", "chmod",
        "chown", "chown32", "clock_getres", "clock_gettime",
        "clock_nanosleep", "close", "connect", "copy_file_range",
        "creat", "dup", "dup2", "dup3", "epoll_create",
        "epoll_create1", "epoll_ctl", "epoll_ctl_old",
        "epoll_pwait", "epoll_wait", "epoll_wait_old",
        "eventfd", "eventfd2", "execve", "execveat",
        "exit", "exit_group", "faccessat", "fadvise64",
        "fallocate", "fanotify_mark", "fchdir", "fchmod",
        "fchmodat", "fchown", "fchown32", "fchownat",
        "fcntl", "fcntl64", "fdatasync", "fgetxattr",
        "flistxattr", "flock", "fork", "fremovexattr",
        "fsetxattr", "fstat", "fstat64", "fstatat64",
        "fstatfs", "fstatfs64", "fsync", "ftruncate",
        "ftruncate64", "futex", "futimesat", "getcpu",
        "getcwd", "getdents", "getdents64", "getegid",
        "getegid32", "geteuid", "geteuid32", "getgid",
        "getgid32", "getgroups", "getgroups32", "getitimer",
        "getpeername", "getpgrp", "getpid", "getppid",
        "getpriority", "getrandom", "getresgid", "getresgid32",
        "getresuid", "getresuid32", "getrlimit", "get_robust_list",
        "getrusage", "getsid", "getsockname", "getsockopt",
        "get_thread_area", "gettid", "gettimeofday", "get_tls",
        "getuid", "getuid32", "getxattr", "inotify_add_watch",
        "inotify_init", "inotify_init1", "inotify_rm_watch",
        "io_cancel", "ioctl", "io_destroy", "io_getevents",
        "io_pgetevents", "ioprio_get", "ioprio_set", "io_setup",
        "io_submit", "io_uring_enter", "io_uring_register",
        "io_uring_setup", "ipc", "kill", "lchown", "lchown32",
        "lgetxattr", "link", "linkat", "listen", "listxattr",
        "llistxattr", "_llseek", "lremovexattr", "lseek",
        "lsetxattr", "lstat", "lstat64", "madvise", "memfd_create",
        "mincore", "mkdir", "mkdirat", "mknod", "mknodat",
        "mlock", "mlock2", "mlockall", "mmap", "mmap2",
        "mprotect", "mq_getsetattr", "mq_notify", "mq_open",
        "mq_timedreceive", "mq_timedsend", "mq_unlink", "mremap",
        "msgctl", "msgget", "msgrcv", "msgsnd", "msync",
        "munlock", "munlockall", "munmap", "nanosleep",
        "newfstatat", "_newselect", "open", "openat",
        "openat2", "pause", "pidfd_open", "pidfd_send_signal",
        "pipe", "pipe2", "poll", "ppoll", "prctl", "pread64",
        "preadv", "preadv2", "prlimit64", "pselect6", "pwrite64",
        "pwritev", "pwritev2", "read", "readahead", "readlink",
        "readlinkat", "readv", "recv", "recvfrom", "recvmmsg",
        "recvmsg", "remap_file_pages", "removexattr", "rename",
        "renameat", "renameat2", "restart_syscall", "rmdir",
        "rseq", "rt_sigaction", "rt_sigpending", "rt_sigprocmask",
        "rt_sigqueueinfo", "rt_sigreturn", "rt_sigsuspend",
        "rt_sigtimedwait", "rt_tgsigqueueinfo", "sched_getaffinity",
        "sched_getattr", "sched_getparam", "sched_get_priority_max",
        "sched_get_priority_min", "sched_getscheduler",
        "sched_rr_get_interval", "sched_setaffinity", "sched_setattr",
        "sched_setparam", "sched_setscheduler", "sched_yield",
        "select", "semctl", "semget", "semop", "semtimedop",
        "send", "sendfile", "sendfile64", "sendmmsg", "sendmsg",
        "sendto", "setfsgid", "setfsgid32", "setfsuid",
        "setfsuid32", "setgid", "setgid32", "setgroups",
        "setgroups32", "setitimer", "setpgid", "setpriority",
        "setregid", "setregid32", "setresgid", "setresgid32",
        "setresuid", "setresuid32", "setreuid", "setreuid32",
        "setrlimit", "set_robust_list", "setsid", "setsockopt",
        "set_thread_area", "set_tid_address", "setuid",
        "setuid32", "setxattr", "shmat", "shmctl", "shmdt",
        "shmget", "shutdown", "sigaltstack", "signalfd",
        "signalfd4", "sigpending", "sigprocmask", "sigreturn",
        "sigsuspend", "socket", "socketcall", "socketpair",
        "splice", "stat", "stat64", "statfs", "statfs64",
        "statx", "symlink", "symlinkat", "sync", "sync_file_range",
        "syncfs", "sysinfo", "tee", "tgkill", "time", "timer_create",
        "timer_delete", "timer_getoverrun", "timer_gettime",
        "timerfd_create", "timerfd_gettime", "timerfd_settime",
        "timer_settime", "times", "tkill", "truncate", "truncate64",
        "ugetrlimit", "umask", "uname", "unlink", "unlinkat",
        "utime", "utimensat", "utimes", "vfork", "vmsplice",
        "wait4", "waitid", "waitpid", "write", "writev"
      ],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

### Custom Seccomp Profile

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "architectures": ["SCMP_ARCH_X86_64"],
  "syscalls": [
    {
      "names": ["read", "write", "open", "close", "stat", "fstat",
                "mmap", "mprotect", "brk", "ioctl", "access",
                "pipe", "select", "sched_yield", "mremap", "msync",
                "dup", "dup2", "nanosleep", "getpid", "socket",
                "connect", "accept", "sendto", "recvfrom",
                "clone", "execve", "exit", "exit_group",
                "openat", "newfstatat", "getrandom", "epoll_create1",
                "epoll_ctl", "epoll_pwait", "futex", "set_tid_address",
                "set_robust_list", "prlimit64", "rseq"],
      "action": "SCMP_ACT_ALLOW"
    }
  ]
}
```

### Docker Compose with Seccomp

```yaml
services:
  app:
    image: nginx:alpine
    container_name: seccomp-app
    security_opt:
      - seccomp:./seccomp-profile.json
    ports:
      - "8080:80"
    restart: unless-stopped
```

## AppArmor (Application Armor)

**AppArmor** is a Linux Security Module (LSM) that enforces Mandatory Access Control (MAC) policies on individual programs. Unlike seccomp, which filters system calls, AppArmor controls **what files a process can access, what capabilities it can use, and what network operations it can perform** — all defined through human-readable profile files.

### Key Features

- **Path-based access control** — restrict file read/write/execute by path
- **Network filtering** — allow/deny specific network protocols and addresses
- **Capability control** — restrict Linux capabilities (CAP_NET_RAW, CAP_SYS_ADMIN)
- **Include profiles** — modular profile composition with abstractions
- **Complain mode** — log violations without enforcing (for testing)
- **Enforce mode** — actively block disallowed operations
- **Docker integration** — load AppArmor profiles at container startup

### AppArmor Profile for a Web Container

```apparmor
#include <tunables/global>

profile docker-nginx flags=(attach_disconnected,mediate_deleted) {
  #include <abstractions/base>
  
  network inet tcp,
  network inet6 tcp,
  
  # Allow reading nginx configuration
  /etc/nginx/** r,
  /usr/sbin/nginx mr,
  
  # Allow serving web content
  /var/www/** r,
  /var/cache/nginx/** rw,
  /var/log/nginx/** rw,
  
  # Allow pid file
  /run/nginx.pid rw,
  
  # Allow Unix sockets
  /run/*.sock rw,
  
  # Deny access to sensitive paths
  deny /etc/shadow rwx,
  deny /etc/passwd w,
  deny /root/** rwx,
  
  # Allow DNS resolution
  /etc/resolv.conf r,
  /etc/hosts r,
  /etc/nsswitch.conf r,
  /etc/host.conf r,
  /etc/gai.conf r,
  
  # Deny raw network access
  deny network raw,
  
  # Deny capability escalation
  deny capability,
}
```

### Docker Compose with AppArmor

```yaml
services:
  app:
    image: nginx:alpine
    container_name: apparmor-app
    security_opt:
      - apparmor:docker-nginx
    ports:
      - "8080:80"
    restart: unless-stopped
```

```bash
# Load the AppArmor profile
sudo apparmor_parser -r /etc/apparmor.d/docker-nginx

# Check profile status
sudo aa-status

# Put profile in complain mode for testing
sudo aa-complain /etc/apparmor.d/docker-nginx

# Switch to enforce mode
sudo aa-enforce /etc/apparmor.d/docker-nginx
```

## Firejail

**Firejail** is a user-space SUID sandbox program that uses Linux namespaces, seccomp filters, and other kernel features to create restricted execution environments for applications. While Docker provides container-level isolation, Firejail operates at the **application level**, creating a sandbox around individual programs running on the host or inside containers.

### Key Features

- **2,000+ pre-built profiles** — profiles for browsers, media players, development tools
- **Network isolation** — private network namespaces with custom IP/MAC
- **X11 sandboxing** — prevent keyloggers and screen scrapers
- **Filesystem isolation** — whitelist/blacklist filesystem access with tmpfs overlays
- **Seccomp integration** — applies its own seccomp filters on top of the kernel
- **No configuration needed** — `firejail firefox` just works
- **AppArmor integration** — can enforce AppArmor profiles within the sandbox

### Firejail Profile for a Container Application

```bash
# Run an application in a Firejail sandbox
firejail --net=eth0 --ip=192.168.1.100 nginx

# Restrict filesystem access
firejail --whitelist=/var/www --whitelist=/etc/nginx \
         --blacklist=/root --blacklist=/home \
         nginx

# Private network with custom DNS
firejail --net=eth0 --dns=8.8.8.8 --dns=8.8.4.4 nginx

# Combine with AppArmor profile
firejail --apparmor=docker-nginx nginx
```

```ini
# /etc/firejail/nginx.local
# Custom Firejail profile for nginx

include /etc/firejail/defaults.profile

# Network isolation
net eth0
ip 192.168.1.100/24
defaultgw 192.168.1.1
dns 8.8.8.8

# Filesystem restrictions
whitelist /var/www
whitelist /etc/nginx
whitelist /var/log/nginx
whitelist /run/nginx.pid
blacklist /root
blacklist /home
blacklist /etc/shadow

# Seccomp filter
seccomp
!socket AF_PACKET

# No new privileges
nonewprivs

# Drop capabilities
caps.drop all
```

## Comparison Table

| Feature | Seccomp | AppArmor | Firejail |
|---------|---------|----------|----------|
| **Level** | Kernel syscall filter | Kernel MAC (LSM) | User-space sandbox |
| **Primary Scope** | System calls | File/network/capability access | Application execution |
| **Configuration** | JSON BPF profiles | Text profile files | CLI flags + profile files |
| **Ease of Use** | Complex (requires syscall knowledge) | Moderate (path-based rules) | Easy (pre-built profiles) |
| **Docker Integration** | Native (--security-opt seccomp) | Native (--security-opt apparmor) | Manual (run inside/outside) |
| **Granularity** | Syscall-level | Path + capability + network | Namespace + filesystem + network |
| **Default Profiles** | Docker default (44 blocked syscalls) | Docker default | 2,000+ application profiles |
| **Audit Mode** | Audit via strace/bpftrace | Complain mode (log only) | --audit flag |
| **Performance Overhead** | Minimal (BPF filter) | Low (LSM hooks) | Low (namespace isolation) |
| **Cross-Distro** | Yes (all Linux kernels) | Yes (AppArmor enabled kernels) | Yes (userspace tool) |
| **Best For** | Blocking dangerous syscalls | Fine-grained access control | Quick application sandboxing |

## Defense-in-Depth Strategy

The most secure container deployments combine all three mechanisms:

1. **Seccomp** — block dangerous system calls (mount, ptrace, kernel module loading)
2. **AppArmor** — restrict file access to only what the application needs
3. **Firejail** — add user-space isolation for applications running directly on the host

```bash
# Example: Multi-layer container security
docker run \
  --security-opt seccomp=./custom-seccomp.json \
  --security-opt apparmor=docker-app-profile \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  --read-only \
  --tmpfs /tmp \
  nginx:alpine
```

## Why Self-Host Your Container Security Profiles?

Managing seccomp and AppArmor profiles yourself gives you precise control over what each container can do. Cloud container platforms apply generic security profiles that may be either too permissive for your threat model or too restrictive for your application's needs. By maintaining your own profiles, you can tailor syscall filters and access controls to each specific workload.

Self-hosted security profiles also support compliance requirements. Financial services, healthcare, and government regulations often mandate specific access controls and audit capabilities. Custom AppArmor profiles provide file-level access logging, while seccomp profiles ensure that only approved system calls can execute — both critical for demonstrating compliance during security audits.

The operational benefits extend to incident response. When a container is compromised, well-configured seccomp and AppArmor profiles limit the attacker's ability to escalate privileges, access sensitive files, or establish reverse shells. An AppArmor profile that denies access to `/etc/shadow` and blocks raw network sockets significantly constrains what a compromised container process can achieve.

For teams managing dozens of containerized services, a centralized profile management system ensures consistency across environments. Store your seccomp profiles and AppArmor configurations in version control, audit changes through pull requests, and deploy updated profiles alongside application releases. This GitOps approach to container security means your security posture evolves with your application, rather than remaining a static configuration that quickly becomes outdated.


## Why Self-Host Your Database Security and Routing Infrastructure?

For deeper container isolation, see our [gVisor vs Kata Containers vs Firecracker sandboxing guide](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/) for kernel-level separation beyond seccomp. Our [Docker Bench vs Trivy vs Checkov hardening guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/) covers broader container security practices. For runtime threat detection, the [NeuVector vs Falco vs Tetragon comparison](../2026-04-29-neuvector-vs-falco-vs-tetragon-container-runtime-security-guide-2026/) monitors for security violations after containers are deployed.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Seccomp Profile Management: AppArmor vs Seccomp vs Firejail (2026)",
  "description": "Manage container security profiles using Seccomp, AppArmor, and Firejail. Learn syscall filtering, MAC policies, and user-space sandboxing for hardened Docker deployments.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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

### What happens when a container violates a seccomp rule?

When a process in seccomp mode attempts a blocked system call, the kernel takes the action defined in the profile. The default action is typically `SCMP_ACT_ERRNO` (return an error code to the process) or `SCMP_ACT_KILL` (terminate the process immediately). Docker's default profile uses `SCMP_ACT_ERRNO`, which causes the syscall to fail with `EPERM` (Operation not permitted) rather than killing the container. For maximum security, you can use `SCMP_ACT_KILL` to terminate any process that violates the seccomp policy.

### Can I use AppArmor and seccomp together on the same container?

Yes, and you should. AppArmor and seccomp operate at different levels and complement each other. Seccomp filters system calls before they reach the kernel, while AppArmor controls what the process can access once the syscall is allowed. Using both provides defense-in-depth: seccomp blocks entire categories of syscalls, while AppArmor fine-tunes access within the allowed syscalls. Docker supports both simultaneously via `--security-opt seccomp=...` and `--security-opt apparmor=...`.

### How do I test an AppArmor profile before enforcing it?

AppArmor has a "complain mode" that logs policy violations without blocking the operation. Load your profile with `sudo aa-complain /etc/apparmor.d/your-profile`, run your application normally, then check the audit log with `sudo journalctl -k | grep audit` or `sudo dmesg | grep DENIED`. Once you are confident the profile allows all necessary operations, switch to enforce mode with `sudo aa-enforce /etc/apparmor.d/your-profile`.

### Does Firejail work inside Docker containers?

Firejail can run inside containers, but it requires the container to have sufficient privileges (specifically, the ability to create new namespaces). Since most security-hardened containers drop capabilities and use restrictive seccomp profiles, Firejail may not function correctly. The more common pattern is to use Firejail for applications running directly on the host, while using Docker's built-in seccomp and AppArmor support for containerized applications.

### How do I find which syscalls my application needs for a custom seccomp profile?

Use `strace` to capture all system calls made by your application: `strace -f -o syscall-log.txt your-command`. Then extract unique syscall names from the log and add them to your seccomp profile's allowlist. Alternatively, use the `seccomp-tools` gem (`gem install seccomp-tools`) to analyze existing profiles or generate new ones from strace output. Start with Docker's default profile as a baseline and remove syscalls your application does not need.

### What is the performance impact of seccomp and AppArmor on containers?

The performance impact is negligible for most workloads. Seccomp uses BPF filters that are compiled to native code and run in the kernel — the overhead is typically less than 1% for normal application workloads. AppArmor's LSM hooks add minimal overhead, primarily on file access operations where path matching occurs. The only measurable impact is during application startup when profiles are loaded and initial path checks run. For high-throughput network services, neither seccomp nor AppArmor will be a bottleneck.

