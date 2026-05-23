---
title: "Self-Hosted Linux PID Namespace Isolation — unshare vs Bubblewrap vs nsenter"
date: "2026-05-24"
tags: ["linux-namespaces", "container-isolation", "process-management", "pid-namespace", "system-administration"]
draft: false
---

Linux PID namespaces provide process ID isolation — processes in different namespaces can have the same PID without conflict. This is the foundation of container process isolation. This guide compares three approaches to PID namespace management: **unshare** (kernel namespace creation), **Bubblewrap** (user-space sandboxing), and **nsenter** (namespace entry for debugging).

## What Are Linux PID Namespaces?

A PID namespace creates an isolated process ID space. The first process in a new namespace gets PID 1, and processes outside the namespace are invisible from within. Key benefits:

- **Process isolation** — Processes cannot see or signal processes in other namespaces
- **Clean PID 1** — Each namespace has its own init process (PID 1)
- **Container foundation** — Docker, Kubernetes, and LXC all use PID namespaces
- **Resource isolation** — Combined with other namespaces for full container isolation

Linux supports multiple namespace types, and PID namespaces are typically combined with mount, network, IPC, and user namespaces for complete isolation.

## unshare: Creating New Namespaces

**GitHub**: kernel source (util-linux package) | **Stars**: N/A (in-tree)

`unshare` is a util-linux utility that creates new namespaces and executes a command within them. It is the most direct way to create PID namespaces from the command line.

### Key Features

- **Direct kernel access** — Uses `unshare()` system call directly
- **All namespace types** — PID, mount, network, IPC, user, UTS, cgroup
- **Flexible configuration** — Mix and match namespace types per use case
- **Script-friendly** — Simple command-line interface for automation

### Basic PID Namespace Creation

```bash
# Create a new PID namespace
sudo unshare --pid --fork --mount-proc /bin/bash

# Inside the new namespace:
ps aux  # Shows only processes in this namespace
# PID 1 is /bin/bash
```

### Full Isolation with Multiple Namespaces

```bash
# Create isolated environment with PID, mount, network, and IPC namespaces
sudo unshare   --pid   --fork   --mount-proc   --mount   --net   --ipc   --uts   /bin/bash

# Inside: complete isolation
hostname isolated-host
ip addr show
ps aux
```

### Docker Compose with unshare

```yaml
version: "3.8"
services:
  unshare-service:
    image: alpine:latest
    # unshare requires capabilities
    cap_add:
      - SYS_ADMIN
    security_opt:
      - apparmor:unconfined
    volumes:
      - ./app:/app:ro
      - ./data:/data
    command: >
      unshare --pid --fork --mount-proc
      --mount --net --ipc
      /app/start.sh
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

### PID Namespace Options

| Flag | Namespace Type | Purpose |
|---|---|---|
| `--pid` | PID | Process ID isolation |
| `--fork` | — | Fork before exec (required for PID) |
| `--mount-proc` | Mount | New /proc for PID namespace |
| `--mount` | Mount | Mount point isolation |
| `--net` | Network | Network stack isolation |
| `--ipc` | IPC | Inter-process communication isolation |
| `--uts` | UTS | Hostname/domain isolation |
| `--user` | User | User ID mapping |
| `--cgroup` | Cgroup | Cgroup namespace |

## Bubblewrap: User-Space Namespace Management

**GitHub**: https://github.com/containers/bubblewrap | **Stars**: 3,100+

Bubblewrap (bwrap) provides user-space namespace management with a more convenient interface than raw `unshare`. It is designed specifically for application sandboxing, combining PID, mount, user, and IPC namespaces with filesystem virtualization.

### Key Features

- **No root required** — Uses unprivileged user namespaces (CONFIG_USER_NS)
- **Filesystem virtualization** — Bind mounts, tmpfs overlays, devtmpfs
- **Pre-configured sandbox** — Sensible defaults for application isolation
- **Flatpak integration** — Powers Flatpak application sandboxing

### Basic Usage

```bash
# Run a command in an isolated PID namespace
bwrap   --unshare-pid   --unshare-user   --unshare-ipc   --unshare-mount   --ro-bind /usr /usr   --ro-bind /etc /etc   --dir /tmp   --proc /proc   --dev /dev   /bin/bash

# Inside: PID 1 is /bin/bash
ps aux  # Only sees processes in this namespace
```

### Application Sandbox Example

```bash
# Sandbox a web browser
bwrap   --unshare-all   --share-net   --ro-bind /usr /usr   --ro-bind /etc /etc   --bind ~/.config/browser ~/.config/browser   --dir /tmp   --proc /proc   --dev /dev   --die-with-parent   firefox
```

### Docker Compose with Bubblewrap

```yaml
version: "3.8"
services:
  bwrap-service:
    image: ubuntu:22.04
    security_opt:
      - apparmor:unconfined
      - seccomp:unconfined
    volumes:
      - ./app:/app:ro
      - ./config:/config
    command: >
      bwrap
      --unshare-pid
      --unshare-user
      --unshare-ipc
      --unshare-mount
      --ro-bind /usr /usr
      --ro-bind /etc /etc
      --bind /config /config
      --dir /tmp
      --proc /proc
      --dev /dev
      --die-with-parent
      /app/server
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

## nsenter: Entering Existing Namespaces

**GitHub**: kernel source (util-linux package) | **Stars**: N/A (in-tree)

`nsenter` enters an existing namespace rather than creating a new one. This is essential for debugging containerized processes, inspecting isolated environments, and managing services running inside namespaces.

### Key Features

- **Namespace inspection** — Enter any namespace by PID or namespace file descriptor
- **Debugging** — Access processes inside containers without exec
- **Multi-namespace entry** — Enter multiple namespaces simultaneously
- **Non-invasive** — Does not modify the target namespace

### Basic Usage

```bash
# Find the PID of a process in a container
container_pid=$(docker inspect -f '{{.State.Pid}}' my-container)

# Enter the PID namespace of that container
sudo nsenter --target $container_pid --pid --mount --net --ipc /bin/bash

# Now inside the container's namespaces
ps aux  # Sees the same processes as the container
ip addr show  # Sees the container's network
```

### Entering Specific Namespaces

```bash
# Enter only the PID namespace
sudo nsenter --target 1234 --pid /bin/bash

# Enter PID and mount namespaces
sudo nsenter --target 1234 --pid --mount /bin/bash

# Enter all namespaces except user
sudo nsenter --target 1234   --pid --mount --net --ipc --uts   /bin/bash
```

### Using Namespace File Descriptors

```bash
# Find namespace file descriptors
ls -la /proc/1234/ns/
# lrwxrwxrwx 1 root root 0 pid -> pid:[4026532297]
# lrwxrwxrwx 1 root root 0 mnt -> mnt:[4026532296]

# Enter using namespace FD
sudo nsenter --pid=/proc/1234/ns/pid --mount=/proc/1234/ns/mnt /bin/bash
```

## Comparison: unshare vs Bubblewrap vs nsenter

| Feature | unshare | Bubblewrap | nsenter |
|---|---|---|---|
| **Purpose** | Create namespaces | Sandbox applications | Enter existing namespaces |
| **PID Namespace** | Yes (`--pid`) | Yes (`--unshare-pid`) | Yes (`--pid`) |
| **Requires Root** | Yes (most namespaces) | No (unprivileged) | Yes (for target PID) |
| **Creates New** | Yes | Yes | No (enters existing) |
| **Filesystem Setup** | Manual | Automatic (bind mounts) | Inherits target |
| **User Namespaces** | Yes | Yes (default) | Yes |
| **Network** | `--net` (new) | `--unshare-net` or `--share-net` | `--net` (enter) |
| **Best For** | Custom namespace setup | Application sandboxing | Container debugging |
| **Complexity** | Low | Medium | Low |
| **Scriptability** | Excellent | Good | Excellent |

## When to Use Each Tool

### Use unshare When:
- You need **fine-grained control** over which namespaces to create
- You are writing **automation scripts** that need namespace isolation
- You need to **combine specific namespace types** (e.g., PID + mount but not network)

### Use Bubblewrap When:
- You need **unprivileged sandboxing** (no root access)
- You are sandboxing **desktop or user applications**
- You want **pre-configured filesystem isolation** with bind mounts

### Use nsenter When:
- You need to **debug processes** inside containers
- You need to **inspect namespace state** without modifying it
- You need to **run commands** in an existing container's namespace

## Why Self-Host PID Namespace Management?

Self-hosted servers run multiple services that benefit from process isolation. Understanding and managing PID namespaces enables:

**Service isolation** — Running untrusted workloads (user scripts, CI jobs, webhooks) in isolated PID namespaces prevents process enumeration and cross-service signaling attacks.

**Container debugging** — When containers malfunction, `nsenter` provides direct access to the container's namespaces for inspection and troubleshooting without relying on container runtime tools.

**Custom sandboxing** — For services that don't run in containers, `unshare` provides a lightweight way to create process isolation without the overhead of a full container runtime.

**Multi-tenant security** — Self-hosted platforms serving multiple users benefit from per-user PID namespaces, ensuring that users cannot see each other's processes or send signals across tenant boundaries.

For container image inspection, see our [container image analysis guide](../2026-05-24-self-hosted-container-image-analysis-tools-dive-skopeo-crane-guide/). For Linux sandboxing frameworks, our [Landlock vs Seccomp vs Bubblewrap comparison](../2026-05-24-self-hosted-linux-sandboxing-frameworks-landlock-seccomp-bubblewrap-guide/) covers complementary isolation mechanisms.

## FAQ

### What is a PID namespace in Linux?

A PID namespace creates an isolated process ID space. The first process in a new namespace gets PID 1, and processes outside the namespace are invisible from within. This is the foundation of container process isolation — Docker, Kubernetes, and LXC all use PID namespaces to isolate container processes from the host.

### Does `unshare --pid` require root access?

Yes, creating a new PID namespace typically requires root access (CAP_SYS_ADMIN capability). However, if your kernel supports unprivileged user namespaces (CONFIG_USER_NS), you can create PID namespaces as a regular user by first creating a user namespace with `unshare --user --map-root-user`.

### Can I enter a container's PID namespace without `docker exec`?

Yes. Using `nsenter`, you can enter any process's namespaces if you know its PID: `nsenter --target <PID> --pid --mount --net /bin/bash`. This is useful when Docker is not available or when you need to inspect namespaces that `docker exec` doesn't expose.

### What is the difference between `unshare` and `nsenter`?

`unshare` **creates** new namespaces and executes a command within them. `nsenter` **enters** existing namespaces of a running process. They are complementary: use `unshare` to set up isolation, and `nsenter` to debug or inspect isolated environments.

### How does Bubblewrap differ from Docker?

Bubblewrap provides user-space namespace isolation for individual applications, while Docker provides full container orchestration with image management, networking, and volume management. Bubblewrap is lighter weight and doesn't require a daemon, making it suitable for desktop application sandboxing (Flatpak) and quick process isolation.

### Can PID namespaces be nested?

Yes. Linux supports nested PID namespaces — a process can create a new PID namespace from within an existing one. Each nested namespace gets its own PID 1 and cannot see processes in parent or sibling namespaces. Docker containers typically use a single level of PID namespace nesting.

### What happens to PID 1 in a namespace?

PID 1 in a namespace has special responsibilities: it must handle orphaned child processes (reaping zombies) and respond to signals properly. If PID 1 exits, the entire namespace is terminated. This is why container init processes (tini, dumb-init) are recommended — they handle these responsibilities correctly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux PID Namespace Isolation — unshare vs Bubblewrap vs nsenter",
  "description": "Comprehensive guide to Linux PID namespace management: unshare (namespace creation), Bubblewrap (user-space sandboxing), and nsenter (namespace entry) for self-hosted server process isolation.",
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
