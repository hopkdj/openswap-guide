---
title: "containerd vs CRI-O vs Podman: Best Self-Hosted Container Runtimes 2026"
date: 2026-04-18
tags: ["comparison", "guide", "self-hosted", "containers", "kubernetes", "docker"]
draft: false
description: "Compare containerd, CRI-O, and Podman — three leading OCI-compliant container runtimes. Learn which one fits your self-hosted infrastructure, from Kubernetes clusters to rootless development environments."
---

Every container you run — whether it's a web server, database, or microservice — depends on a **container runtime** underneath. The runtime is the low-level software that actually creates, manages, and tears down containers on your host system.

For most of [docker](https://www.docker.com/)'s history, the runtime was bundled together with the CLI, networking, and image management into one monolithic tool. But the ecosystem has since split into specialized, modular components. Today, three OCI-compliant runtimes dominate the self-hosted landscape: **containerd**, **CRI-O**, and **Podman**.

Choosing the right on[kubernetes](https://kubernetes.io/) It affects your Kubernetes compatibility, security posture, operational com[plex](https://www.plex.tv/)ity, and whether you can run containers without root privileges.

For related reading, see our [Kubernetes distribution comparison](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/) for runtime integration details, our [container build tools guide](../buildah-vs-kaniko-vs-earthly-self-hosted-container-build-tools-guide-2026/) for image creation workflows, and our [container registry comparison](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide-2026/) for image storage options.

## Why Run Your Own Container Runtime?

Cloud providers abstract the container runtime away from you. But when you self-host, you own the full stack — and the runtime choice has real consequences:

- **Security**: Rootless container execution eliminates entire classes of privilege escalation attacks
- **Resource efficiency**: Lightweight runtimes use less RAM and CPU on the host, leaving more for your workloads
- **Compliance**: Some regulated environments require you to control every layer of the infrastructure stack
- **Vendor independence**: Avoiding Docker Desktop licensing fees and vendor lock-in
- **Kubernetes compatibility**: Different runtimes integrate differently with the kubelet via the Container Runtime Interface (CRI)

Understanding these trade-offs starts with knowing what each runtime is designed to do.

## What Is containerd?

**containerd** is the industry-standard container runtime that powers Docker, Kubernetes, and countless other projects. Originally extracted from Docker's internals, it became a standalone CNCF graduated project and is now maintained by the Cloud Native Computing Foundation.

**GitHub stats (April 2026):**
- ⭐ 20,594 stars
- 🍴 3,875 forks
- 📅 Last active: April 17, 2026
- 📄 License: Apache-2.0

containerd sits between high-level orchestrators and low-level runtimes like runc. It handles image management, container lifecycle, storage, and networking — but deliberately avoids the CLI and Compose layers. It's designed as a daemon that other tools talk to via gRPC.

### Key Features

- **CNCF Graduated** status with enterprise-grade stability
- **CRI plugin** built in — provides the Kubernetes Container Runtime Interface out of the box
- **Namespace isolation** — multiple tenants can share one containerd daemon safely
- **Snapshotter plugins** — supports overlayfs, btrfs, zfs, and native snapshotters
- **NRI (Node Resource Interface)** — allows third-party plugins to hook into container lifecycle events
- **Content-addressable storage** — images are stored and deduplicated efficiently

### Installing containerd

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y containerd
sudo systemctl enable --now containerd
```

Generate the default configuration:

```bash
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml
sudo systemctl restart containerd
```

Verify installation:

```bash
ctr version
# Client:
#   Version:  2.1.4
#   Runtime:  io.containerd.runc.v2
```

### Using containerd with Kubernetes

containerd is the default runtime for most Kubernetes distributions. The CRI plugin exposes the necessary endpoints automatically:

```toml
# /etc/containerd/config.toml
[plugins."io.containerd.grpc.v1.cri"]
  sandbox_image = "registry.k8s.io/pause:3.9"

  [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc]
    runtime_type = "io.containerd.runc.v2"
    [plugins."io.containerd.grpc.v1.cri".containerd.runtimes.runc.options]
      SystemdCgroup = true
```

For interacting with containerd directly (without Docker), use the `ctr` CLI:

```bash
# Pull an image
sudo ctr images pull docker.io/library/nginx:latest

# Run a container
sudo ctr run -d --net-host docker.io/library/nginx:latest my-nginx

# List containers
sudo ctr containers list
```

Note that `ctr` is a debug/admin tool, not a production workflow tool. For day-to-day operations, most users interact with containerd through Docker, Kubernetes, or higher-level tooling.

## What Is CRI-O?

**CRI-O** is a lightweight container runtime built specifically for Kubernetes. Developed by Red Hat and part of the Kubernetes incubator projects, it implements only the Kubernetes Container Runtime Interface — nothing more, nothing less.

**GitHub stats (April 2026):**
- ⭐ 5,601 stars
- 🍴 1,161 forks
- 📅 Last active: April 17, 2026
- 📄 License: Apache-2.0

Where containerd tries to be a general-purpose runtime, CRI-O is laser-focused on being the best possible runtime for Kubernetes. It strips away everything that isn't needed for CRI compliance, resulting in a smaller attack surface and simpler operational model.

### Key Features

- **Kubernetes-native** — purpose-built for the CRI specification
- **Minimal attack surface** — no Docker API compatibility, no general-purpose container management
- **Multiple OCI runtimes** — supports runc, crun, and Kata Containers via configuration
- **Image pulling from any registry** — supports Docker, OCI, and signed images with sigstore
- **Integrated with OpenShift** — the default runtime for Red Hat's Kubernetes distribution
- **CRI stats API** — exposes container and pod metrics for monitoring

### Installing CRI-O

On Ubuntu/Debian:

```bash
# Set up the repository
OS=xUbuntu_24.04
VERSION=1.31

echo "deb https://pkgs.k8s.io/addons:/cri-o:/stable:/v${VERSION}/deb/ /" | \
  sudo tee /etc/apt/sources.list.d/cri-o.list
sudo apt-get update
sudo apt-get install -y cri-o
sudo systemctl enable --now crio
```

Verify installation:

```bash
crictl info
# Output shows CRI-O version, runtime configuration, and network settings
```

### Configuring CRI-O

The main configuration file is `/etc/crio/crio.conf`:

```toml
[crio]
log_level = "info"

[crio.runtime]
default_runtime = "crun"
conmon_cgroup = "pod"

[crio.runtime.runtimes.crun]
runtime_path = "/usr/bin/crun"
runtime_type = "oci"

[crio.image]
default_transport = "docker://"
pause_image = "registry.k8s.io/pause:3.9"
pause_command = "/pause"

[crio.network]
network_dir = "/etc/cni/net.d/"
plugin_dirs = ["/opt/cni/bin/", "/usr/libexec/cni/"]
```

Using CRI-O with crun (a faster C alternative to runc):

```bash
sudo apt-get install -y crun

# Update CRI-O config to use crun
sudo sed -i 's/default_runtime = "runc"/default_runtime = "crun"/' /etc/crio/crio.conf
sudo systemctl restart crio
```

## What Is Podman?

**Podman** (POD MANager) is a daemonless, rootless container engine developed by Red Hat as part of the containers project. Unlike containerd and CRI-O, Podman provides both the runtime AND the CLI in a single tool — designed as a drop-in replacement for the Docker CLI.

**GitHub stats (April 2026):**
- ⭐ 31,432 stars
- 🍴 3,062 forks
- 📅 Last active: April 17, 2026
- 📄 License: Apache-2.0

Podman's most distinctive feature is that it runs **without a daemon**. Every `podman run` command spawns a direct process tree — no background service to manage, no single point of failure. It also supports **rootless containers** out of the box using user namespaces.

### Key Features

- **Daemonless architecture** — no persistent daemon; containers are direct child processes
- **Rootless by default** — runs containers as non-root users via user namespaces (userns)
- **Docker CLI compatible** — `alias docker=podman` works for most workflows
- **Pod management** — groups containers into pods (shared network namespace), similar to Kubernetes pods
- **Quadlet integration** — systemd-native container management via `.container` and `.pod` files
- **Podman Compose** — Docker Compose file compatibility via a separate tool
- **Buildah integration** — shares the image build tool from the same project family

### Installing Podman

On Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install -y podman
```

On Fedora/RHEL (usually pre-installed):

```bash
sudo dnf install -y podman
```

Verify installation:

```bash
podman --version
# podman version 5.4.0
```

### Running Containers with Podman

Basic usage mirrors Docker exactly:

```bash
# Pull and run a web server
podman run -d --name web -p 8080:80 docker.io/library/nginx:latest

# Run rootless (no sudo needed for most images)
podman run -d --name app -p 3000:3000 docker.io/library/node:20-alpine

# List running containers
podman ps
```

### Using Quadlet for Systemd Integration

Quadlet lets you manage containers as native systemd units — the most robust way to run production containers on a self-hosted server:

```ini
# /etc/containers/systemd/web.container
[Container]
Image=docker.io/library/nginx:latest
ContainerName=web
PublishPort=8080:80
Volume=/srv/web/html:/usr/share/nginx/html:ro
RestartPolicy=always

[Install]
WantedBy=default.target
```

Enable and start:

```bash
systemctl daemon-reload
systemctl enable --now web.container
```

This replaces Docker Compose restart policies and supervisor processes with systemd's battle-tested service management.

## Comparison: containerd vs CRI-O vs Podman

| Feature | containerd | CRI-O | Podman |
|---------|-----------|-------|--------|
| **Primary use case** | General-purpose runtime, Kubernetes default | Kubernetes-only runtime | Developer workstation, daemonless servers |
| **Daemon required** | Yes (containerd daemon) | Yes (crio daemon) | No (daemonless) |
| **Rootless support** | No | Partial (via crun) | Yes (native, default) |
| **Kubernetes CRI** | Yes (built-in CRI plugin) | Yes (purpose-built for CRI) | Via Podman kube play / kubelet integration |
| **Docker CLI compatibility** | No (via Docker daemon) | No | Yes (`alias docker=podman`) |
| **Compose support** | Via Docker Compose | No | Via podman-compose |
| **Pod management** | No | Via Kubernetes pods | Yes (native pod concept) |
| **Systemd integration** | Via systemd service | Via systemd service | Via Quadlet (.container files) |
| **Stars on GitHub** | 20,594 | 5,601 | 31,432 |
| **OCI compliance** | Full | Full | Full |
| **Low-level runtime** | runc, crun, others | runc, crun, Kata | runc, crun |
| **Image build** | No (external) | No (external) | Yes (via Buildah integration) |
| **Best for** | Kubernetes clusters, Docker backend | Minimal Kubernetes nodes | Development, rootless production, systemd-native workflows |

## When to Use Each Runtime

### Choose containerd if:

- You're running a **Kubernetes cluster** and want the battle-tested default
- You need **multi-tenant isolation** via containerd namespaces
- You want broad ecosystem compatibility (Docker uses it internally)
- You need **NRI plugins** for custom resource management hooks
- You're building a platform on top of containers and need a stable gRPC API

containerd is the safe, proven choice. It's what Kubernetes used by default after Docker was deprecated as a runtime in v1.24. Most managed Kubernetes services run containerd underneath.

### Choose CRI-O if:

- Your **only workload is Kubernetes** — no other container use cases
- You want the **smallest possible runtime** footprint on each node
- You're running **OpenShift** or a Red Hat-based distribution
- Security audit requirements demand the **minimal attack surface**
- You want to use **crun** as the default low-level runtime for faster startup

CRI-O is the specialist. It does one thing extremely well and nothing else. If you don't need Docker API compatibility, general-purpose container management, or daemonless operation, CRI-O is the leanest option.

### Choose Podman if:

- You want a **Docker replacement** on your workstation or server
- You need **rootless containers** for security compliance
- You prefer **systemd-native** container management via Quadlet
- You want to run **container pods** without Kubernetes
- You're a developer who wants the Docker CLI experience without the Docker daemon

Podman is the generalist for non-Kubernetes workloads. It covers the same ground that Docker does — image management, container lifecycle, Compose compatibility — but with a more secure, daemonless architecture.

## Security Comparison

### Rootless Execution

| Runtime | Rootless Mode | Implementation |
|---------|--------------|----------------|
| containerd | Not supported natively | Requires root for the daemon; containers run as the daemon user |
| CRI-O | Via crun user namespaces | Kubernetes manages user namespace mapping through the CRI spec |
| Podman | Native, default mode | Uses Linux user namespaces (`unshare --map-root-user`) for full rootless isolation |

Podman's rootless support is the most mature. It uses subuid/subgid mappings to give each container its own uid range:

```bash
# Check your user namespace mapping
cat /etc/subuid
# youruser:100000:65536

# Run a container completely rootless
podman run --rm -it docker.io/library/alpine:latest whoami
# root (but this is mapped to your non-root host user)
```

### Image Signing and Verification

All three runtimes support image verification, but the mechanisms differ:

```bash
# containerd: uses cosign for signature verification
ctr content fetch --all-platforms docker.io/library/nginx:latest
# Verification via external cosign tool

# CRI-O: built-in sigstore/cosign support
# /etc/crio/crio.conf
[crio.image]
signature_policy = "/etc/containers/policy.json"

# Podman: built-in signature verification
podman image trust set -t reject default
podman image trust set -t signedAccept registry.example.com
```

## Performance Benchmarks

Based on publicly available benchmarks and community testing:

| Metric | containerd | CRI-O + crun | Podman + crun |
|--------|-----------|-------------|---------------|
| Container start time | ~200ms | ~150ms | ~180ms |
| Memory overhead (daemon) | ~50MB | ~30MB | 0MB (daemonless) |
| Image pull throughput | Fast | Fast | Fast |
| Concurrent containers | 10,000+ | 10,000+ | Limited by user session |

CRI-O with crun tends to have the fastest container startup because it has the least abstraction layer between the kubelet and the OCI runtime. Podman's daemonless model means zero baseline memory overhead — but each session has its own overhead, which can add up on systems running many isolated containers.

## Migration Paths

### From Docker to containerd

If you're currently using Docker Engine and want to understand what's underneath:

```bash
# Docker already uses containerd
docker info | grep -A2 "Container Runtime"
# Container Runtime: containerd

# To use containerd directly (without Docker):
sudo systemctl stop docker
sudo systemctl start containerd
# Use ctr or nerdctl for CLI operations
```

For a drop-in Docker CLI replacement that uses containerd underneath, consider **nerdctl**:

```bash
# Install nerdctl
sudo apt-get install -y nerdctl

# Works like docker but talks directly to containerd
nerdctl run -d -p 80:80 nginx:latest
nerdctl compose up -d  # Docker Compose compatible
```

### From Docker to Podman

The migration is nearly seamless:

```bash
# Install podman and podman-docker (provides docker CLI shim)
sudo apt-get install -y podman podman-docker

# Your existing docker commands work unchanged
docker run -d -p 80:80 nginx:latest
# Actually runs: podman run -d -p 80:80 nginx:latest

# Migrate existing Docker images
podman load -i docker-images.tar
# Or pull fresh from registry
podman pull docker.io/library/nginx:latest
```

## Frequently Asked Questions

### Can I use Podman with Kubernetes?

Yes, but not as a direct kubelet runtime. Podman supports `podman play kube` to deploy Kubernetes YAML files directly:

```bash
podman play kube my-deployment.yaml
```

For running Podman containers inside Kubernetes pods, you can use Podman as a runtime via the CRI-O-compatible `podman-remote` socket, but this is not a common production pattern. For Kubernetes clusters, containerd or CRI-O are the recommended choices.

### Is containerd a replacement for Docker?

Not directly. containerd is the runtime that Docker uses internally. If you remove Docker, you lose the Docker CLI, Compose support, and image building. To replace Docker with containerd, you need additional tools like **nerdctl** for the CLI and **BuildKit** for image building. Podman is a more direct Docker replacement since it includes the CLI and build capabilities.

### Which runtime is most secure for production?

For **rootless operation**, Podman is the clear winner — it supports rootless containers natively with minimal configuration. For **Kubernetes workloads**, CRI-O has the smallest attack surface because it implements only the CRI specification and nothing else. For **general-purpose servers**, containerd with proper namespace isolation and network policies provides enterprise-grade security.

### Can I switch runtimes on an existing Kubernetes cluster?

Yes, but it requires draining nodes and changing the kubelet configuration. The process involves:

```bash
# On each node:
sudo systemctl stop containerd
sudo systemctl disable containerd

sudo systemctl start crio
sudo systemctl enable crio

# Update kubelet to point to the new runtime socket
sudo sed -i 's|--container-runtime-endpoint.*|--container-runtime-endpoint=unix:///var/run/crio/crio.sock|' /var/lib/kubelet/kubeadm-flags.env
sudo systemctl restart kubelet
```

Always test in a non-production environment first. Not all container images behave identically across runtimes.

### Does CRI-O support Docker Compose files?

No. CRI-O is purpose-built for Kubernetes and does not support Docker Compose or any standalone container management. If you need Compose support alongside Kubernetes, pair CRI-O (for Kubernetes) with Podman or containerd+nerdctl (for standalone workloads) on the same node.

### What is the difference between runc and crun?

Both are OCI-compliant low-level container runtimes. **runc** is the reference implementation written in Go, used by default in Docker and containerd. **crun** is a faster alternative written in C, with lower memory usage and faster startup times. CRI-O supports both, and Podman can use either. Switching to crun typically reduces container startup time by 20-30%.

### How do I monitor container runtime performance?

For containerd, use the built-in metrics endpoint:

```bash
# containerd metrics (Prometheus format)
curl http://localhost:1338/v1/metrics
```

For CRI-O, use `crictl stats`:

```bash
crictl stats --all
# CONTAINER           CPU %   MEM     NET       BLOCK
# abc123              0.12    45MB    1.2KB/s   0B/s
```

For Podman, use `podman stats`:

```bash
podman stats --all
# ID            NAME        CPU %   MEM USAGE   MEM %   NET IO    BLOCK IO
# abc123        web         0.15    48.2MB      2.3%    1KB/0B    0B/0B
```

## Summary

| Criteria | containerd | CRI-O | Podman |
|----------|-----------|-------|--------|
| **Best for** | Kubernetes + general purpose | Kubernetes-only | Development + rootless production |
| **Complexity** | Medium | Low | Low-Medium |
| **Security** | Good (daemonized) | Excellent (minimal) | Excellent (rootless) |
| **Kubernetes** | Native (default) | Native (purpose-built) | Limited (play kube) |
| **Standalone containers** | Via nerdctl | Not supported | Native |
| **Learning curve** | Moderate | Low | Low (Docker-compatible CLI) |

For a complete container ecosystem, consider combining these with our guides on [container build tools](../buildah-vs-kaniko-vs-earthly-self-hosted-container-build-tools-guide-2026/) for image creation, [container registries](../harbor-vs-distribution-vs-zot-self-hosted-container-registry-guide-2026/) for image storage, and [Kubernetes distributions](../k3s-vs-k0s-vs-talos-linux-self-hosted-kubernetes-guide-2026/) for orchestration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "containerd vs CRI-O vs Podman: Best Self-Hosted Container Runtimes 2026",
  "description": "Compare containerd, CRI-O, and Podman — three leading OCI-compliant container runtimes. Learn which one fits your self-hosted infrastructure, from Kubernetes clusters to rootless development environments.",
  "datePublished": "2026-04-18",
  "dateModified": "2026-04-18",
  "author": {
    "@type": "Organization",
    "name": "OpenSwap Guide"
  },
  "publisher": {
    "@type": "Organization",
    "name": "OpenSwap Guide",
    "logo": {
      "@type": "ImageObject",
      "url": "https://www.pistack.xyz/logo.png"
    }
  }
}
</script>
