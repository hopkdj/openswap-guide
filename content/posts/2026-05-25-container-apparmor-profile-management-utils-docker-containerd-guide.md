---
title: "Self-Hosted Container AppArmor Profile Management: AppArmor Utils vs Docker AppArmor vs Containerd AppArmor"
date: "2026-05-25"
tags: ["container-security", "apparmor", "linux-security", "docker", "containerd", "mandatory-access-control"]
draft: false
---

Container runtimes provide process isolation through namespaces and cgroups, but these mechanisms alone do not restrict what a container process can do on the host kernel. AppArmor (Application Armor) is a Linux Security Module (LSM) that enforces mandatory access control policies, restricting container processes to only the system resources they explicitly need.

This guide compares three approaches to managing AppArmor profiles for containers: standalone AppArmor utilities (`apparmor-utils`), Docker's built-in AppArmor integration, and containerd's native AppArmor profile support. We cover profile creation, deployment, and best practices for securing containerized workloads in self-hosted environments.

## Understanding AppArmor for Containers

AppArmor works by attaching security profiles to processes via the Linux Security Module (LSM) framework. Each profile defines which files, network ports, and capabilities a process can access. For containers, AppArmor profiles are applied when the container runtime starts the container process.

Without AppArmor, a root process inside a container can potentially:
- Access sensitive host files through mount namespaces
- Load kernel modules if capabilities are not properly restricted
- Access raw sockets or perform network operations beyond what the container needs
- Modify system-wide settings via procfs or sysfs

AppArmor profiles restrict these operations at the kernel level, providing defense-in-depth beyond container runtime security settings.

| Feature | AppArmor Utils | Docker AppArmor | Containerd AppArmor |
|---------|---------------|-----------------|---------------------|
| Package | apparmor-utils | docker-ce (built-in) | containerd (built-in) |
| Profile Location | /etc/apparmor.d/ | /etc/apparmor.d/ (or inline) | /etc/apparmor.d/ (or inline) |
| Profile Syntax | AppArmor DSL | AppArmor DSL | AppArmor DSL |
| Management CLI | aa-genprof, aa-enforce, aa-complain | docker run --security-opt | containerd CRI config |
| Default Profile | No (manual) | docker-default (included) | cri-default (CRI) |
| Custom Profiles | Yes | Yes | Yes |
| Profile Enforcement | Kernel LSM | Runtime-applied at container start | Runtime-applied at container start |
| Profile Switching | aa-enforce/aa-complain | Container restart required | Container restart required |
| Kubernetes Support | Manual | Via runtime config | Native (via CRI) |
| Best For | Host-level security | Docker environments | Kubernetes/containerd environments |

## AppArmor Utils: Standalone Profile Management

`apparmor-utils` provides command-line tools for creating, managing, and enforcing AppArmor profiles. This approach is ideal for host-level container security management.

### Installation

```bash
# Debian/Ubuntu
apt-get update && apt-get install -y apparmor apparmor-utils

# Verify AppArmor is active
aa-status

# Check kernel module
systemctl status apparmor
```

### Generating Profiles with aa-genprof

`aa-genprof` interactively generates profiles by monitoring an application's behavior:

```bash
# Start profiling a container runtime
aa-genprof /usr/bin/containerd-shim

# Or profile a specific application
aa-genprof /usr/sbin/nginx

# The tool monitors the application and prompts for each access request
# Answer Allow/Deny for each operation, then save the profile
```

### Writing Custom AppArmor Profiles

Create a profile in `/etc/apparmor.d/`:

```bash
cat > /etc/apparmor.d/docker-restricted << 'EOF'
#include <tunables/global>

profile docker-restricted flags=(attach_disconnected) {
  #include <abstractions/base>
  #include <abstractions/nameservice>

  # Allow reading standard library files
  /lib/** mr,
  /usr/lib/** mr,

  # Allow network access (TCP/UDP)
  network inet tcp,
  network inet udp,
  network inet6 tcp,
  network inet6 udp,

  # Restrict file system access
  deny /etc/shadow r,
  deny /etc/gshadow r,
  deny /etc/passwd w,
  deny /proc/sys/** w,
  deny /sys/** w,

  # Allow working directory
  /var/lib/docker/containers/** rw,

  # Deny kernel module loading
  deny capability sys_module,
  deny capability sys_admin,
}
EOF

# Load and enforce the profile
apparmor_parser -r /etc/apparmor.d/docker-restricted
aa-enforce docker-restricted
```

### Managing Profile States

```bash
# List all loaded profiles
aa-status

# Switch a profile to complain mode (log violations, don't block)
aa-complain docker-restricted

# Switch to enforce mode (block and log violations)
aa-enforce docker-restricted

# Disable a profile
aa-disable docker-restricted

# Remove a profile
apparmor_parser -R /etc/apparmor.d/docker-restricted
```

## Docker AppArmor Integration

Docker includes a default AppArmor profile (`docker-default`) that provides a reasonable baseline for container security. Custom profiles can be applied per-container.

### Default Docker AppArmor Profile

Docker ships with a default profile that:
- Allows basic system calls required by most containers
- Blocks access to `/proc/sys`, `/sys/fs`, and other sensitive paths
- Restricts kernel module loading
- Allows network access (TCP/UDP)
- Denies raw socket access

To check the default profile:

```bash
# View Docker's default AppArmor profile
docker info | grep -i apparmor

# Or inspect the profile file
cat /etc/apparmor.d/docker
```

### Applying Custom AppArmor Profiles to Docker Containers

```bash
# Run a container with a custom AppArmor profile
docker run --security-opt "apparmor=docker-restricted"   --name my-app   -d nginx:latest

# Run with no AppArmor profile (not recommended)
docker run --security-opt "apparmor=unconfined"   --name my-debug   -d ubuntu:latest

# Verify AppArmor profile is applied
docker inspect my-app --format '{{.AppArmorProfile}}'
```

### Docker Compose with AppArmor

```yaml
version: "3.8"
services:
  web-app:
    image: nginx:latest
    security_opt:
      - apparmor=docker-restricted
    ports:
      - "80:80"
    restart: unless-stopped

  database:
    image: postgres:16
    security_opt:
      - apparmor=database-restricted
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  pgdata:
```

### Generating Docker-Specific Profiles

```bash
# Use aa-logprof to refine a profile based on actual container activity
aa-logprof

# This analyzes AppArmor log entries and suggests profile updates
# Review each suggestion and accept or deny
```

## Containerd AppArmor Support

containerd supports AppArmor profiles through its CRI (Container Runtime Interface) implementation. This is the primary mechanism for applying AppArmor in Kubernetes environments.

### Configuring Default AppArmor in containerd

```bash
# Edit containerd configuration
cat > /etc/containerd/config.toml << 'EOF'
version = 2

[plugins."io.containerd.grpc.v1.cri".containerd]
  default_runtime_name = "runc"

[plugins."io.containerd.grpc.v1.cri"]
  # Set default AppArmor profile for all containers
  apparmor_profile = "cri-default"
EOF

# Restart containerd
systemctl restart containerd
```

### Applying AppArmor Profiles via CRI

When using containerd directly (not through Kubernetes):

```bash
# Use ctr with AppArmor profile
ctr run --with-ns="network:/var/run/netns/myns"   --apparmor-profile=cri-default   docker.io/library/nginx:latest my-nginx
```

### Kubernetes AppArmor Integration

Kubernetes supports AppArmor through annotations:

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: secured-pod
  annotations:
    # Apply AppArmor profile to all containers in the pod
    container.apparmor.security.beta.kubernetes.io/web: runtime/default
    container.apparmor.security.beta.kubernetes.io/sidecar: localhost/custom-profile
spec:
  containers:
    - name: web
      image: nginx:latest
    - name: sidecar
      image: busybox:latest
```

The `runtime/default` annotation applies the container runtime's default profile (containerd's `cri-default` or Docker's `docker-default`). The `localhost/profile-name` annotation applies a custom profile from `/etc/apparmor.d/`.

## Container AppArmor Profile for Database Services

Here's a production-ready AppArmor profile for a database container:

```bash
cat > /etc/apparmor.d/database-restricted << 'EOF'
#include <tunables/global>

profile database-restricted flags=(attach_disconnected) {
  #include <abstractions/base>
  #include <abstractions/nameservice>
  #include <abstractions/openssl>

  # Database data directory
  /var/lib/postgresql/** rw,
  /var/lib/mysql/** rw,

  # Configuration files (read-only)
  /etc/postgresql/** r,
  /etc/mysql/** r,

  # Log files
  /var/log/postgresql/** rw,
  /var/log/mysql/** rw,

  # Network access for database connections
  network inet tcp,
  network inet6 tcp,

  # Deny dangerous capabilities
  deny capability sys_admin,
  deny capability sys_module,
  deny capability sys_rawio,
  deny capability sys_ptrace,

  # Deny access to sensitive host paths
  deny /proc/sys/** w,
  deny /sys/** w,
  deny /dev/** rw,
  deny /etc/shadow r,
  deny /root/** r,

  # Allow standard libraries
  /lib/** mr,
  /usr/lib/** mr,
}
EOF

apparmor_parser -r /etc/apparmor.d/database-restricted
aa-enforce database-restricted
```

## Docker Compose Full Stack with AppArmor

```yaml
version: "3.8"
services:
  web:
    image: nginx:latest
    security_opt:
      - apparmor=web-restricted
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped

  app:
    image: node:20-alpine
    security_opt:
      - apparmor=app-restricted
    working_dir: /app
    command: ["node", "server.js"]
    restart: unless-stopped

  db:
    image: postgres:16
    security_opt:
      - apparmor=database-restricted
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    restart: unless-stopped

volumes:
  pgdata:
```

## Choosing the Right AppArmor Management Approach

| Scenario | Recommended Approach | Reason |
|----------|---------------------|--------|
| Docker-only environment | Docker built-in profiles | Seamless integration, default profile included |
| Kubernetes clusters | Containerd AppArmor via annotations | Native CRI support, per-pod granularity |
| Mixed runtime environment | AppArmor utils (standalone) | Runtime-agnostic, works with any container engine |
| Custom security requirements | Custom profiles + aa-genprof | Fine-grained control over each service |
| Compliance (PCI, HIPAA) | Custom enforced profiles | Audit-ready, verifiable security policies |

For broader container sandboxing, see our [container sandboxing comparison](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/) covering gVisor, Kata, and Firecracker. For container security hardening beyond access control, our [Docker Bench vs Trivy vs Checkov guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide/) covers automated security auditing. For seccomp-based syscall filtering, check our [seccomp profile management article](../2026-05-10-container-seccomp-profile-management-apparmor-firejail-guide/).

## FAQ

### What is AppArmor and why should I use it with containers?

AppArmor is a Linux Security Module that provides mandatory access control (MAC). It restricts what files, network ports, and capabilities a process can access. While container runtimes provide namespace and cgroup isolation, AppArmor adds kernel-level enforcement that prevents container escape even if a process gains root privileges inside the container. It is defense-in-depth for containerized workloads.

### How does AppArmor differ from seccomp for container security?

AppArmor and seccomp serve different purposes. AppArmor controls **what resources** a process can access (files, network, capabilities). Seccomp controls **which system calls** a process can make. They are complementary: seccomp blocks dangerous syscalls (like `mount`, `ptrace`), while AppArmor restricts file and network access. Use both for comprehensive container security.

### Can I use AppArmor profiles with Docker Compose?

Yes. Add `security_opt: - apparmor=profile-name` to each service in your `docker-compose.yml`. The profile must be loaded on the host system before starting the containers. Docker automatically applies the profile when creating the container.

### How do I create an AppArmor profile for my application?

Use `aa-genprof /path/to/binary` to start interactive profile generation. Run your application normally, and `aa-genprof` will monitor all access attempts. When the application tries to access a resource, `aa-genprof` prompts you to allow or deny the access. After completing the session, save the profile and switch to enforce mode.

### What happens if an AppArmor profile blocks a legitimate container operation?

Switch the profile to complain mode with `aa-complain profile-name`. In complain mode, violations are logged but not blocked. Review the logs with `aa-logprof` to identify which rules need adjustment. Once the profile is correct, switch back to enforce mode with `aa-enforce profile-name`.

### Are AppArmor profiles shared across containers?

Yes. AppArmor profiles are defined at the host level and can be applied to any container. Multiple containers can use the same profile, or each container can have its own profile. Profiles are loaded into the kernel once and reused.

### How do I verify AppArmor is active on my system?

Run `aa-status` to see loaded profiles and their enforcement state. Check `cat /sys/kernel/security/lsm` to see if AppArmor is in the active LSM list. Also check `dmesg | grep apparmor` for kernel-level AppArmor messages.

### Why Self-Host Container Security?

Self-hosted container environments require security controls that match or exceed managed cloud offerings. AppArmor provides enterprise-grade mandatory access control without additional infrastructure or licensing costs. Combined with seccomp profiles, read-only filesystems, and dropped capabilities, AppArmor forms a critical layer in container security hardening.

For organizations running self-hosted Kubernetes, AppArmor profiles complement Kubernetes Pod Security Standards by providing host-level enforcement that survives container restarts and runtime changes. For Docker-based deployments, AppArmor prevents container escape even if application vulnerabilities are exploited.

For Linux kernel security auditing, see our [kernel security guide](../2026-05-23-self-hosted-linux-kernel-security-auditing-kconfig-hardened-check-checksec-guide/). For Linux-level sandboxing frameworks, our [landlock and firejail comparison](../2026-05-24-self-hosted-linux-sandboxing-frameworks-landlock-firejail-bubblewrap-guide/) covers alternative approaches.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container AppArmor Profile Management: AppArmor Utils vs Docker AppArmor vs Containerd AppArmor",
  "description": "Compare three approaches to managing AppArmor profiles for containers: standalone apparmor-utils, Docker built-in integration, and containerd native support. Includes custom profiles and Docker Compose configs.",
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
