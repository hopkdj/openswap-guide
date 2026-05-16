---
title: "Self-Hosted OCI Runtime Hooks: umoci vs oci-seccomp-bpf-hook vs oci-add-hooks"
date: "2026-05-16"
tags: ["containers", "oci", "docker", "runtime", "hooks"]
draft: false
---

OCI (Open Container Initiative) runtime hooks allow you to execute custom logic at specific points during a container lifecycle — before it starts, after it stops, or during creation. These hooks enable powerful customization: injecting environment variables, setting up network namespaces, applying seccomp profiles dynamically, or mounting filesystems on-the-fly. In this guide, we compare three open-source OCI hook implementations and show you how to deploy each with Docker Compose.

## What Are OCI Runtime Hooks?

The OCI Runtime Specification defines a hook mechanism that lets you run custom executables at defined lifecycle events. Hooks are specified in the container config.json and are triggered by the runtime (runc, crun, containerd) during container operations:

- **createRuntime** — runs after the container namespace is created but before the process starts
- **createContainer** — runs after the container root filesystem is mounted
- **startContainer** — runs just before the container process executes
- **poststart** — runs after the container process starts (asynchronously)
- **poststop** — runs after the container process terminates

Hooks receive the container state via stdin and environment variables, allowing them to inspect the container PID, bundle path, and annotation data before taking action. This design enables deeply customized container behavior without modifying the container image itself.

## Tool Comparison

| Feature | umoci | oci-seccomp-bpf-hook | oci-add-hooks |
|---|---|---|---|
| GitHub Stars | 923+ | 348+ | 66+ |
| Primary Use | Image modification + hooks | Auto-generate seccomp profiles | Inject hooks into Docker |
| Language | Go | Go + eBPF | Go |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| Docker Integration | Manual bundle editing | runc hook registration | Docker daemon patching |
| Standalone Tool | Yes | Yes (runc hook) | Yes (daemon plugin) |
| Kubernetes Support | Via CRI-O annotations | Via RuntimeClass | Limited |
| Last Updated | Active (2026) | Active (2026) | Active (2026) |
| Organization | opencontainers | containers (Red Hat) | AWS Labs |

### umoci — The Swiss Army Knife

[umoci](https://github.com/opencontainers/umoci) is the most versatile OCI hook tool. Originally built for image modification, it includes hook implementations for setting up default bridge networking, binding devices, and executing arbitrary commands during container lifecycle events.

```bash
# Install umoci
curl -LO https://github.com/opencontainers/umoci/releases/latest/download/umoci.amd64
chmod +x umoci.amd64
sudo mv umoci.amd64 /usr/local/bin/umoci

# Use umoci to unpack and modify an OCI image
umoci unpack --rootless --image docker://alpine:latest rootfs
umoci config --config rootfs/config.json --author "admin@example.com"

# Re-pack the modified image
umoci repack --image docker://my-alpine:v2 rootfs
```

umoci hook system works by modifying the OCI bundle config.json directly. You can add hooks to any pre-existing image, making it ideal for CI/CD pipelines that need to inject custom behavior into third-party container images.

### oci-seccomp-bpf-hook — Automatic Seccomp Profiling

The [oci-seccomp-bpf-hook](https://github.com/containers/oci-seccomp-bpf-hook) from the containers organization uses eBPF to trace syscalls during container startup and automatically generates a minimal seccomp profile. This is far more precise than writing seccomp rules by hand.

```bash
# Install the hook
go install github.com/containers/oci-seccomp-bpf-hook@latest

# Generate a seccomp profile by running the container once
oci-seccomp-bpf-hook --output seccomp-profile.json --exec /bin/sh

# Apply the generated profile
podman run --security-opt seccomp=./seccomp-profile.json myapp
```

The hook traces all syscalls during the first run, then produces a whitelist profile that blocks everything else. This is the principle of least privilege automated — no manual syscall auditing required.

### oci-add-hooks — Docker Hook Injection

AWS Labs [oci-add-hooks](https://github.com/awslabs/oci-add-hooks) patches the Docker daemon to inject OCI hooks into containers without modifying their configuration files. This is useful when you want to apply hooks to third-party images you do not control.

```yaml
# docker-compose.yml for oci-add-hooks
services:
  docker-with-hooks:
    image: awslabs/oci-add-hooks:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /etc/oci-hooks:/etc/oci-hooks:ro
    environment:
      - OCI_HOOKS_DIR=/etc/oci-hooks
    restart: unless-stopped
    network_mode: host
    pid: host
```

## Why Self-Host OCI Hooks?

Running OCI hooks in your own infrastructure gives you complete control over container lifecycle behavior without relying on cloud provider extensions or proprietary runtime modifications. Self-hosted hooks enable custom network setup, security hardening with seccomp profiles and AppArmor rules, resource injection for configuration files and secrets, telemetry integration with monitoring systems, and compliance enforcement against organizational policies.

When you manage your own hook infrastructure, you avoid vendor lock-in to specific container platforms. OCI hooks work across runc, crun, containerd, CRI-O, and any runtime that implements the OCI Runtime Specification. This portability is a significant advantage over platform-specific alternatives.

## Deployment with Docker Compose

### umoci Hook Setup

```yaml
services:
  app-with-umoci:
    image: myapp:latest
    volumes:
      - ./hooks:/etc/oci-hooks:ro
    deploy:
      restart_policy:
        condition: on-failure
    labels:
      - "oci.hook.prestart=/etc/oci-hooks/umoci-setup.sh"
```

### seccomp-bpf-hook with runc

```yaml
services:
  app-with-seccomp:
    image: myapp:latest
    security_opt:
      - seccomp=./generated-seccomp.json
    volumes:
      - /etc/containers/containers.conf:/etc/containers/containers.conf:ro
```

## Best Practices for OCI Hook Deployment

When deploying OCI runtime hooks in production, follow these operational guidelines. Always version your hook scripts alongside your container images — use git tags or image digests to ensure hooks match the exact image version they were tested against. Store hook binaries in immutable, read-only locations that only the root user or the container runtime can access.

Implement hook timeout policies. The OCI spec does not define timeout behavior for hooks, so a hanging hook will block all container operations on that runtime. Use wrapper scripts that enforce timeouts with a 30-second ceiling. Monitor hook execution times and failure rates by logging hook start/end timestamps and exit codes to your centralized logging system. Set up alerts for hook failures since a failing prestart hook prevents all container startups on that node.

For multi-tenant Kubernetes clusters, use namespace-scoped hook configurations. CRI-O supports hook annotations that can be scoped to specific namespaces, allowing different teams to define their own hook behavior without affecting the entire cluster.

## Choosing the Right OCI Hook Tool

The right choice depends on your operational model. If you build container images in CI/CD and want hooks baked into the image itself, umoci is the natural fit. If you are running containers on Podman or CRI-O and want automatic seccomp hardening, the oci-seccomp-bpf-hook delivers the best security posture. If you are managing Docker infrastructure and need to inject hooks into existing containers without rebuilding images, oci-add-hooks provides that capability.

For container runtime security best practices, see our [container security hardening guide](../2026-04-27-docker-bench-vs-trivy-vs-checkov-self-hosted-container-security-hardening-guide-2026/). If you are exploring container image security further, our [supply chain security article](../2026-04-21-self-hosted-supply-chain-security-cosign-notation-intoto-2026/) covers signing and verification. For runtime threat detection, check our [container runtime security comparison](../2026-04-29-neuvector-vs-falco-vs-tetragon-container-runtime-security-guide-2026/).

## Security Considerations for Container Lifecycle Hooks

Container lifecycle hooks operate at a privileged level within the container runtime, which introduces several security considerations that operators must address before deploying hooks in production environments. Hook scripts execute with the same privileges as the container runtime process, which typically means root access on the host system. This means any vulnerability in a hook script, such as a command injection through unsanitized environment variables or container annotations, could lead to full host compromise.

The attack surface extends beyond the hook script itself. Hook configuration files, binary paths, and annotation values must all be validated and protected. Use read-only filesystem mounts for hook directories, implement file integrity monitoring with tools like AIDE or OSSEC, and restrict hook binary execution through AppArmor or SELinux policies. Never store hook credentials or secrets in hook configuration files — use a secrets management system and retrieve secrets at runtime through secure channels.

Network access from hook scripts should be carefully controlled. If a hook makes outbound network calls to configuration servers, monitoring endpoints, or secret stores, ensure those connections use TLS with certificate validation. Implement network policies that restrict hook outbound traffic to only the necessary endpoints. Log all hook network activity for security audit purposes.


## FAQ

### What are OCI runtime hooks used for?

OCI runtime hooks execute custom code at specific points during a container lifecycle — before the process starts (prestart), after it starts (poststart), and after it stops (poststop). Common uses include setting up network namespaces, applying security profiles, injecting configuration, and integrating with monitoring systems.

### Are OCI hooks supported by Docker?

Docker has limited native support for OCI hooks. The Docker daemon does not directly read hook configurations from the OCI bundle. Tools like oci-add-hooks work around this by patching Docker to inject hooks. Podman and CRI-O have better native OCI hook support through their configuration files.

### Can OCI hooks access the host filesystem?

OCI hooks run in the host PID namespace and have access to the host filesystem. They execute as the same user as the container runtime (typically root). This means hooks must be carefully secured — a compromised hook script has full host access.

### How do I debug a failing OCI hook?

Check the container runtime logs. For runc, hooks output to stderr which is captured by the runtime. For Podman, check journalctl -u podman. For CRI-O, check journalctl -u crio. The OCI spec requires hooks to exit with code 0 for success — any non-zero exit aborts the container operation.

### Can I use OCI hooks with Kubernetes?

Yes, but indirectly. CRI-O supports OCI hooks through its configuration file. You can register hooks that apply to all containers or filter by annotation. containerd supports hooks via its runtime configuration. The Kubernetes API itself does not have a native hook concept — hooks are a runtime-level feature.

### What security risks do OCI hooks introduce?

OCI hooks run with host-level privileges, making them a potential attack vector. If a hook script is writable by an unprivileged user, it could be modified to execute arbitrary code with root access. Always store hooks in read-only directories, use file integrity monitoring, and restrict hook execution to trusted binaries only.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted OCI Runtime Hooks: umoci vs oci-seccomp-bpf-hook vs oci-add-hooks",
  "description": "Compare three open-source OCI runtime hook implementations — umoci, oci-seccomp-bpf-hook, and oci-add-hooks — with Docker Compose deployment guides and security best practices.",
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
