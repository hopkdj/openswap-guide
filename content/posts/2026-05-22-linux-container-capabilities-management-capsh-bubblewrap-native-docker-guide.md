---
title: "Self-Hosted Linux Container Capabilities Management: capsh vs bubblewrap vs Native Docker Capabilities (2026)"
date: "2026-05-22"
tags: ["containers", "linux-capabilities", "security", "docker", "bubblewrap", "sandbox"]
draft: false
---

Linux capabilities split the all-powerful root privilege into distinct units. Instead of running a container as full root (with access to every kernel operation), you can grant only the specific capabilities it needs. This guide compares three approaches to managing container capabilities: **native Docker/Kubernetes capability controls**, **capsh** (capability shell), and **bubblewrap** (unprivileged sandbox).

## Understanding Linux Capabilities

Before Linux 2.2, every privileged operation required the superuser (UID 0) role. This meant a compromised root process had unlimited access to the system. Linux capabilities introduced a finer-grained model: the root role is split into ~40 distinct privileges, each controlling specific kernel operations.

Key capabilities for container workloads include:

- **CAP_NET_ADMIN**: Network configuration (interfaces, routes, firewall rules)
- **CAP_SYS_ADMIN**: Broad system administration (mount, namespace, cgroup operations)
- **CAP_DAC_OVERRIDE**: Bypass file read/write/execute permission checks
- **CAP_NET_RAW**: Use RAW and PACKET sockets (packet sniffing)
- **CAP_SYS_PTRACE**: Trace processes (debugging, monitoring)
- **CAP_CHOWN**: Change file ownership
- **CAP_FOWNER**: Bypass permission checks on operations requiring file owner ID match

A container running with `--privileged` gets ALL capabilities — equivalent to running as root on the host. A non-privileged container gets a default subset (roughly 14 capabilities). The security best practice is to drop all capabilities and add back only what's needed.

For related container security topics, see our [Container Security Hardening guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide/) and our [Container Seccomp Profile Management guide](../2026-05-10-container-seccomp-profile-management-apparmor-firejail-guide/). For runtime security monitoring, check our [Kubearmor vs Falco vs Tetragon guide](../2026-05-07-kubearmor-vs-falco-vs-tetragon-runtime-security-guide/).

## Native Docker/Kubernetes Capability Controls

Docker and Kubernetes provide built-in mechanisms to control container capabilities without additional tools.

### Docker Capabilities

Docker uses `--cap-add` and `--cap-drop` flags to manage capabilities:

```bash
# Drop all capabilities, add only NET_BIND_SERVICE
docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE nginx

# Drop all, add network capabilities for a proxy
docker run --cap-drop=ALL   --cap-add=NET_BIND_SERVICE   --cap-add=NET_RAW   --cap-add=NET_ADMIN   haproxy:2.9

# List effective capabilities inside a running container
docker exec <container> capsh --print
```

### Docker Compose Configuration

```yaml
version: "3.8"

services:
  webserver:
    image: nginx:alpine
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    ports:
      - "80:80"
      - "443:443"
    security_opt:
      - no-new-privileges:true
    restart: unless-stopped

  database:
    image: postgres:16-alpine
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
      - FOWNER
      - SETGID
      - SETUID
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pgdata:
```

### Kubernetes SecurityContext

Kubernetes controls capabilities via the `securityContext`:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secure-app
spec:
  containers:
  - name: app
    image: nginx:alpine
    securityContext:
      capabilities:
        drop:
          - ALL
        add:
          - NET_BIND_SERVICE
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 1000
    ports:
    - containerPort: 8080
```

### Kubernetes Pod Security Standards

At the cluster level, Pod Security Standards (PSS) enforce capability policies:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: restricted-ns
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

The `restricted` policy drops ALL capabilities and prevents adding any back.

## capsh (Capability Shell)

[capsh](https://man7.org/linux/man-pages/man1/capsh.1.html) is part of the `libcap` package and provides a shell environment with specific capability sets. It's used for testing, debugging, and running processes with controlled capabilities.

### Installation

```bash
# Debian/Ubuntu
apt-get install -y libcap2-bin

# Alpine
apk add libcap
```

### Usage Examples

```bash
# Print current capabilities
capsh --print

# Run a command with specific capabilities
capsh --caps="cap_net_admin,cap_net_raw+eip" -- -c "ip addr show"

# Drop all capabilities and run a shell
capsh --drop=all -- -c "whoami && capsh --print"

# Test if a capability is available
capsh --print | grep -i "cap_net_admin"
```

### Dockerfile with capsh for Testing

```dockerfile
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y libcap2-bin && rm -rf /var/lib/apt/lists/*

# Create a test script
RUN echo '#!/bin/bash
capsh --print' > /test-caps.sh && chmod +x /test-caps.sh

# Run with capsh to verify capability drop
CMD ["capsh", "--drop=all", "--", "-c", "/test-caps.sh"]
```

### Key Features

- **Part of libcap**: Official Linux capability library, available on all distributions
- **Interactive testing**: Test capability configurations before deploying
- **Debugging**: Print and verify capability sets at runtime
- **Bounding set control**: Manage the bounding set (upper limit of inheritable capabilities)
- **No additional image layers**: Available through standard package managers

### Limitations

- **Not a sandbox**: capsh doesn't isolate namespaces or filesystems — it only controls capabilities
- **Manual configuration**: Requires explicit capability specification for each use case
- **Root requirement**: To set capabilities, you typically need initial root access

## bubblewrap (Unprivileged Sandbox)

[bubblewrap](https://github.com/containers/bubblewrap) is a sandboxing tool that uses Linux namespaces and seccomp to create isolated environments without requiring root privileges. It's the foundation of Flatpak's sandboxing.

### How bubblewrap Works

bubblewrap combines multiple Linux isolation mechanisms:
- **User namespaces**: Maps container UIDs to unprivileged host UIDs
- **Mount namespaces**: Creates isolated filesystem views
- **PID namespaces**: Isolates process visibility
- **seccomp filters**: Blocks dangerous syscalls
- **Capability dropping**: Drops all capabilities by default

### Installation

```bash
# Debian/Ubuntu
apt-get install -y bubblewrap

# Fedora
dnf install -y bubblewrap

# From source
git clone https://github.com/containers/bubblewrap
cd bubblewrap
meson setup build
ninja -C build
```

### Usage Examples

```bash
# Run a command in an isolated sandbox
bwrap --ro-bind /usr /usr       --dir /tmp       --dir /var       --die-with-parent       --unshare-all       /bin/bash

# Sandbox with network access
bwrap --ro-bind /usr /usr       --share-net       --dir /tmp       --die-with-parent       --unshare-all       curl https://example.com

# Bind-mount specific directories (read-only)
bwrap --ro-bind /etc/passwd /etc/passwd       --ro-bind /usr /usr       --bind /home/user/data /data       --dir /tmp       --die-with-parent       --unshare-all       /bin/bash
```

### Docker Compose Alternative: Running Apps via bubblewrap

For applications that don't need full container isolation, bubblewrap can replace Docker:

```yaml
version: "3.8"

services:
  sandbox-app:
    image: ubuntu:24.04
    command: >
      bash -c "
        apt-get update && apt-get install -y bubblewrap &&
        bwrap --ro-bind /usr /usr --dir /tmp --die-with-parent
              --unshare-all --share-net /usr/bin/python3 -m http.server 8080
      "
    ports:
      - "8080:8080"
    security_opt:
      - no-new-privileges:true
```

### Key Features

- **No root required**: Runs entirely in user namespaces, no sudo needed
- **Multiple isolation layers**: Namespaces + seccomp + capabilities combined
- **Fine-grained filesystem control**: Bind-mount specific paths (read-only or read-write)
- **Flatpak foundation**: Battle-tested through millions of Flatpak installations
- **Lightweight**: No daemon, no image layers — just a single binary

### Comparison with Docker

| Feature | bubblewrap | Docker |
|---------|-----------|--------|
| **Root Required** | No (user namespaces) | Yes (for image management) |
| **Image System** | No (uses host filesystem) | Yes (layers, registry) |
| **Networking** | Optional (`--share-net`) | Built-in (bridge, host, overlay) |
| **Capability Control** | All dropped by default | Default subset, configurable |
| **Process Isolation** | PID namespace | PID namespace |
| **Filesystem Isolation** | Bind mounts only | Full overlay filesystem |
| **Best For** | Desktop app sandboxing | Server container orchestration |

## Comparison Table

| Feature | Docker/K8s Native | capsh | bubblewrap |
|---------|-------------------|-------|------------|
| **Capability Control** | `--cap-add`/`--cap-drop` | `--caps`, `--drop` | All dropped by default |
| **Namespace Isolation** | Full (PID, network, mount, etc.) | None | Full (via unshare) |
| **seccomp Filtering** | Yes (customizable profiles) | No | Yes (default profile) |
| **Root Required** | Yes (for Docker daemon) | Yes (to set caps) | No (user namespaces) |
| **Image Management** | Yes (Docker registry) | No | No |
| **Orchestration** | Kubernetes, Docker Compose | Manual | Manual |
| **Complexity** | Low (built-in) | Low (CLI tool) | Medium (namespace config) |
| **Primary Use Case** | Production containers | Capability testing/debugging | Desktop sandboxing |
| **Multi-container** | Yes | No | No |
| **GitHub Stars** | N/A | N/A (libcap) | 2,500+ |

## Security Best Practices

1. **Always drop ALL capabilities first**: Start with `--cap-drop=ALL` and add back only what's needed. This follows the principle of least privilege.

2. **Combine with seccomp**: Capabilities control what privileged operations are allowed; seccomp controls which syscalls can be made. Using both provides defense in depth.

3. **Use `no-new-privileges`**: Set `security_opt: no-new-privileges:true` in Docker or `allowPrivilegeEscalation: false` in Kubernetes to prevent processes from gaining additional privileges via setuid binaries.

4. **Audit capability usage**: Use `capsh --print` inside containers to verify the effective capability set matches your expectations.

5. **Avoid CAP_SYS_ADMIN**: This capability is nearly equivalent to full root. It allows mount operations, namespace manipulation, and many other powerful operations. Only grant it if absolutely necessary.

6. **Use read-only root filesystems**: Combine capability dropping with `readOnlyRootFilesystem: true` to prevent filesystem modifications even if a capability is misused.

## FAQ

### What's the difference between capabilities and seccomp?

Capabilities control what privileged kernel operations a process can perform (mount, network config, etc.). seccomp (secure computing mode) controls which system calls a process can make. They operate at different layers: capabilities are a permission model for specific operations, while seccomp is a syscall filter. Using both together provides stronger security than either alone.

### Can I run Docker containers without any capabilities?

Yes. Use `--cap-drop=ALL` to drop all default capabilities. However, most container images expect at least some capabilities to function. A web server might need `NET_BIND_SERVICE` to listen on port 80. A database might need `CHOWN` and `FOWNER` to manage its data files. Test your application with dropped capabilities and add back only what it needs.

### Is bubblewrap a replacement for Docker?

Not for production server workloads. bubblewrap lacks Docker's image management, networking, orchestration, and multi-container support. It's designed for sandboxing individual desktop applications (which is what Flatpak uses it for). For server containers, use Docker or Kubernetes with proper capability controls.

### How do I find out which capabilities my application needs?

Start by running with all capabilities dropped (`--cap-drop=ALL`) and observe what breaks. Then add capabilities one by one until the application works. Use `capsh --print` inside the container to verify. Alternatively, use `strace` to identify syscalls that fail with `EPERM` (permission denied) — these often indicate missing capabilities.

### What is the capability bounding set?

The bounding set is an upper limit on the capabilities that can ever be acquired by a process and its children. Even if a process has a capability in its permitted set, it cannot gain it if it's not in the bounding set. Docker sets the bounding set based on `--cap-add`/`--cap-drop` flags. capsh can manipulate it with `--bounding-set`.

### Does dropping capabilities affect application performance?

No. Capabilities are a security mechanism, not a performance limiter. Dropping capabilities doesn't slow down your application — it simply prevents the application from performing certain privileged operations. The only "performance" impact is that operations requiring dropped capabilities will fail with permission errors, which is the intended security behavior.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Linux Container Capabilities Management: capsh vs bubblewrap vs Native Docker Capabilities (2026)",
  "description": "Compare three approaches to managing Linux container capabilities: native Docker/Kubernetes controls, capsh capability shell, and bubblewrap sandbox.",
  "datePublished": "2026-05-22",
  "dateModified": "2026-05-22",
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
