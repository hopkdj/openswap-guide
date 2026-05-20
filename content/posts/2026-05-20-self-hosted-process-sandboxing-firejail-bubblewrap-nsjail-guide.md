---
title: "Self-Hosted Process Sandboxing: Firejail vs Bubblewrap vs nsjail (2026)"
date: "2026-05-20"
tags: ["sandboxing", "security", "linux", "namespaces", "containers", "isolation", "seccomp", "self-hosted"]
draft: false
---

Running untrusted or partially trusted code on Linux requires more than basic user permissions. Modern process sandboxing leverages Linux namespaces, seccomp-bpf filters, and cgroup resource limits to create isolated execution environments — without the overhead of full virtual machines or Docker containers.

In this guide, we compare three leading Linux process sandboxing tools: **Firejail**, the user-friendly security sandbox; **Bubblewrap**, the minimal namespace isolation tool used by Flatpak; and **nsjail**, the lightweight security-focused jail from Google designed for competitive programming and untrusted code execution.

## What Is Process Sandboxing?

Process sandboxing restricts what a running program can access on the system by creating isolated namespaces for:

- **Filesystem**: Mount a restricted view of the filesystem, hiding sensitive files
- **Network**: Block or restrict network access entirely
- **PID**: Create a new process ID namespace, hiding other processes
- **IPC/User**: Isolate inter-process communication and user/group mappings
- **Seccomp**: Filter which system calls the process can make
- **Cgroups**: Limit CPU, memory, and I/O resources

Unlike containers (Docker, LXC), these tools work at the process level — no daemon required, no image management, just run a command in a restricted environment.

## Comparison Overview

| Feature | Firejail | Bubblewrap (bwrap) | nsjail |
|---------|----------|-------------------|--------|
| GitHub Stars | 7,394+ | 7,288+ | 3,911+ |
| Language | C | C | C++ |
| Primary Use Case | Desktop app sandboxing | Flatpak runtime isolation | Untrusted code execution |
| Namespace Support | All (mount, pid, net, ipc, uts, user) | All (mount, pid, net, ipc, uts, user) | All (mount, pid, net, ipc, uts, user, cgroup) |
| Seccomp Filtering | Yes (pre-built profiles) | No (relies on host) | Yes (Kafel BPF language) |
| Network Isolation | Private network namespace | Optional (--unshare-net) | Yes (--disable_rl or --port) |
| Filesystem Sandbox | Whitelist/blacklist profiles | Bind mounts only | Bind mounts + pivot_root |
| Configuration | Profile-based (1200+ app profiles) | CLI flags only | Config file or CLI flags |
| Cgroup Support | Limited | No | Yes (v2) |
| Root Required | No (user namespaces) | No (user namespaces) | No (user namespaces) |
| Ease of Use | Very easy (pre-built profiles) | Moderate (manual CLI) | Moderate (config file) |
| Last Updated | May 2026 | May 2026 | May 2026 |

## Firejail

Firejail is the most user-friendly sandboxing tool, with over 1,200 pre-built application profiles for common desktop software. It's designed to protect everyday applications from exploiting system resources.

### Installation

```bash
# Ubuntu/Debian
sudo apt install firejail

# Arch Linux
sudo pacman -S firejail

# From source
git clone https://github.com/netblue30/firejail.git
cd firejail
./configure && make && sudo make install
```

### Basic Usage

```bash
# Run Firefox in a sandbox
firejail firefox

# Run with private network (no network access)
firejail --net=none firefox

# Run with a restricted home directory
firejail --private firefox

# Use a custom profile
firejail --profile=/etc/firejail/firefox.profile firefox
```

### Docker Compose Deployment

For server-side sandboxing, you can deploy Firejail within a container:

```yaml
version: "3.8"
services:
  sandbox:
    image: ubuntu:24.04
    security_opt:
      - apparmor=unconfined
    cap_add:
      - SYS_ADMIN
    volumes:
      - ./sandbox-dir:/sandbox:rw
    command: >
      bash -c "
        apt update && apt install -y firejail &&
        firejail --private=/sandbox --net=none --profile=strict.profile /sandbox/run.sh
      "
```

### Key Features

- **1,200+ application profiles**: Pre-configured sandbox profiles for Firefox, Chrome, VLC, LibreOffice, and more
- **Private mode**: Creates a temporary filesystem view, discarding all changes on exit
- **Network isolation**: Create private virtual networks or completely block network access
- **X11 filtering**: Restrict which X11 windows an application can access
- **CPU/IO limiting**: Built-in resource limiting via cgroups

## Bubblewrap

Bubblewrap is a minimal namespace sandboxing tool, primarily known as the isolation backend for Flatpak desktop applications. It provides raw namespace control without the opinionated defaults of Firejail.

### Installation

```bash
# Ubuntu/Debian
sudo apt install bubblewrap

# Arch Linux
sudo pacman -S bubblewrap

# From source
git clone https://github.com/containers/bubblewrap.git
cd bubblewrap
meson setup build && ninja -C build && sudo ninja -C build install
```

### Basic Usage

```bash
# Run a command with isolated filesystem
bwrap \
  --bind / / \
  --dev /dev \
  --proc /proc \
  --sysfs /sys \
  --tmpfs /tmp \
  --ro-bind /usr /usr \
  --dir /home/user/sandbox \
  --bind /home/user/data /home/user/data \
  /bin/bash

# Run with no network access
bwrap \
  --unshare-net \
  --bind / / \
  --dev /dev \
  --proc /proc \
  /bin/bash

# Run with new PID namespace
bwrap \
  --unshare-pid \
  --bind / / \
  --dev /dev \
  --proc /proc \
  /bin/bash
```

### Key Features

- **Minimal and composable**: Does one thing well — set up namespaces. No opinionated profiles
- **Flatpak backend**: Powers Flatpak application sandboxing on millions of Linux desktops
- **Fine-grained filesystem control**: Bind mount exactly what you need, nothing more
- **No daemon required**: Runs entirely in user space with user namespace support
- **SUID or user namespace mode**: Works on systems without SUID or with kernel user namespace support

## nsjail

nsjail is a security-focused sandboxing tool developed by Google, designed for safely executing untrusted code in competitive programming environments and security testing scenarios.

### Installation

```bash
# From source
git clone https://github.com/google/nsjail.git
cd nsjail
make

# Dependencies: libnl3, protobuf, libprotobuf-dev
sudo apt install libnl-3-dev libnl-genl-3-dev libprotobuf-dev protobuf-compiler
```

### Basic Usage

```bash
# Run a command with strict isolation
nsjail \
  --chroot / \
  --bindmount /usr:/usr:ro \
  --bindmount /lib:/lib:ro \
  --bindmount /lib64:/lib64:ro \
  --bindmount /etc:/etc:ro \
  --disable_rl \
  --port 8080 \
  /bin/bash

# Run with resource limits
nsjail \
  --chroot / \
  --bindmount_ro /usr \
  --rlimit_as 256 \
  --rlimit_cpu 10 \
  --rlimit_fsize 10 \
  --time_limit 30 \
  /bin/bash

# Using a configuration file
nsjail --config /etc/nsjail/sandbox.cfg
```

### Configuration File Example

```protobuf
name: "sandbox"
description: "Untrusted code execution sandbox"

mode: ONCE
hostname: "nsjail"
chroot: "/"

mount {
  src: "/usr"
  dst: "/usr"
  is_bind: true
  rw: false
}

mount {
  src: "/tmp"
  dst: "/tmp"
  is_bind: true
  rw: true
}

rlimit_as: 268435456    # 256 MB memory
rlimit_cpu: 10          # 10 seconds CPU
rlimit_fsize: 10485760  # 10 MB file size
time_limit: 30          # 30 seconds wall clock

keep_env: false
keep_caps: false

disable_no_new_privs: false

seccomp_string: "ALLOW { write, read, exit, exit_group, brk, mmap, mprotect, munmap }"
seccomp_string: "DEFAULT KILL"
```

### Key Features

- **Kafel seccomp language**: Domain-specific language for writing precise syscall filters
- **Resource limits**: Memory, CPU, file size, and time limits via rlimits
- **Chroot support**: Full chroot with selective bind mounts
- **Network sandboxing**: Disable networking or restrict to specific ports
- **Designed for untrusted code**: Built specifically for safely running user-submitted programs
- **Protobuf configuration**: Structured configuration files for complex sandbox setups

## Why Self-Host Process Sandboxing?

Running isolated processes on your own infrastructure provides several advantages over cloud-based sandboxing services:

**Data Privacy**: Sensitive code, documents, and data never leave your servers. This is critical for organizations handling proprietary algorithms, customer data, or regulated content.

**Cost Control**: Cloud sandboxing services charge per-execution or per-hour. Self-hosted sandboxing runs on your existing infrastructure with no per-use fees, making it cost-effective at scale.

**Customization**: Open-source sandboxing tools can be modified to meet specific security requirements. You control the isolation level, resource limits, and audit logging.

**Compliance**: For regulated industries (finance, healthcare, government), self-hosted sandboxing ensures full control over data handling, audit trails, and access controls — requirements that cloud services may not fully satisfy.

For container-level isolation strategies, see our [gVisor vs Kata Containers vs Firecracker comparison](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-containe/). For container security profiles, our [seccomp profile management guide](../2026-05-10-container-seccomp-profile-management-apparmor-fir/) covers kernel-level syscall filtering.

## Choosing the Right Sandboxing Tool

**Firejail** is the best choice for desktop application sandboxing. Its pre-built profiles make it trivial to sandbox common applications like browsers, media players, and office suites. Use it when you want quick, reliable sandboxing without manual configuration.

**Bubblewrap** excels when you need fine-grained, composable namespace isolation. It's the tool of choice for developers building custom sandboxed applications or desktop environments that need precise filesystem control without the overhead of full profiles.

**nsjail** is designed for server-side untrusted code execution. If you're running a code execution service, competitive programming platform, or security testing environment, nsjail's resource limits, seccomp filtering, and chroot support make it the most appropriate choice.

## FAQ

### What is the difference between Firejail and Bubblewrap?

Firejail provides pre-built application profiles with sensible defaults, making it easy to sandbox common desktop applications. Bubblewrap is a minimal tool that sets up Linux namespaces without any opinionated defaults — you configure exactly which filesystem paths, network access, and capabilities the sandboxed process gets. Firejail is easier to use; Bubblewrap is more flexible.

### Can I run Firejail on a server without a desktop environment?

Yes. Firejail works on headless servers. Many of its profiles are for server-side applications (SSH, databases, web servers). The X11-related features simply won't apply on headless systems.

### Does Bubblewrap require root privileges?

Bubblewrap can work without root privileges if the kernel supports user namespaces (most modern Linux kernels do). On systems where user namespaces are disabled, Bubblewrap may need SUID installation or root access.

### How does nsjail compare to Docker for running untrusted code?

nsjail is lighter and faster than Docker because it doesn't manage images, networks, or storage drivers. It's designed specifically for single-process isolation with strict resource limits. Docker is a full container runtime — more features but also more overhead and attack surface.

### Can these sandboxing tools be combined?

Yes. For example, you can use Bubblewrap to set up the filesystem namespaces and then use Firejail's seccomp profiles for syscall filtering. nsjail can be nested inside a Docker container for defense-in-depth sandboxing.

### What Linux kernel features do these tools rely on?

All three tools use Linux namespaces (mount, PID, network, IPC, UTS, user), and optionally cgroups for resource limiting. nsjail additionally uses seccomp-bpf for syscall filtering. These features have been in the Linux kernel since version 3.8+.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Process Sandboxing: Firejail vs Bubblewrap vs nsjail",
  "description": "Compare Linux process sandboxing tools — Firejail, Bubblewrap, and nsjail for secure isolated code execution.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
