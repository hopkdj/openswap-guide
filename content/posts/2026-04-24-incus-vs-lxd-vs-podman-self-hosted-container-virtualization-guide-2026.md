---
title: "Incus vs LXD vs Podman: Self-Hosted Container & System Virtualization Guide 2026"
date: 2026-04-24
tags: ["comparison", "guide", "self-hosted", "virtualization", "containers", "incus", "lxd"]
draft: false
description: "Compare Incus, LXD, and Podman for self-hosted container and system virtualization. Complete guide to installation, configuration, networking, and migration."
---

When you need to run isolated workloads on a self-hosted server, the choice of container or virtualization technology shapes everything — from resource overhead to security boundaries to management complexity. In 2026, three open-source options dominate this space: **Incus**, **LXD**, and **Podman**. Each takes a fundamentally different approach to isolation, and picking the right one depends on whether you need full system containers, daemonless application containers, or a mix of both.

This guide compares all three side by side, covering installation, configuration, networking, storage, and real-world use cases.

## Why Self-Host Your Own Container Platform?

Running your own container and virtualization infrastructure gives you:

- **Full data sovereignty** — no telemetry, no vendor lock-in, no usage limits
- **Zero recurring costs** — all three tools are 100% free and open-source
- **Hardware-level control** — direct GPU passthrough, custom kernel modules, custom networking
- **Lightweight resource usage** — system containers share the host kernel with minimal overhead (typically 2-5% vs 10-20% for full VMs)
- **Unified management** — manage containers, virtual machines, and application containers from a single CLI

For homelab operators, small teams, and organizations running self-hosted infrastructure, these tools provide enterprise-grade isolation without the VMware or Docker Desktop price tag.

## Understanding the Three Approaches

Before comparing features, it helps to understand the architectural differences:

| Feature | Incus | LXD | Podman |
|---------|-------|-----|--------|
| **Type** | System container & VM manager | System container & VM manager | Application container engine |
| **Origin** | Community fork of LXD (2023) | Canonical (original LXD lineage) | Red Hat (Docker-compatible alternative) |
| **Daemon** | Yes (`incusd`) | Yes (`lxd`) | **No** (daemonless) |
| **Rootless** | Partial (via user namespace) | Partial (via user namespace) | **Yes** (fully rootless by default) |
| **OCI Images** | ✅ Supported | ✅ Supported | ✅ Native support |
| **System Containers** | ✅ Primary focus | ✅ Primary focus | ❌ Not designed for |
| **Virtual Machines** | ✅ QEMU/KVM integration | ✅ QEMU/KVM integration | ❌ Not supported |
| **Clustering** | ✅ Native (RAFT-based) | ✅ Native (dqlite-based) | ❌ Requires external orchestrator |
| **GPU Passthrough** | ✅ Yes | ✅ Yes | ❌ Limited |
| **Storage Drivers** | ZFS, Btrfs, LVM, Ceph, dir | ZFS, Btrfs, LVM, Ceph, dir | overlay, vfs, btrfs, zfs |
| **Network Drivers** | Bridge, OVN, MACVLAN | Bridge, OVN, MACVLAN | Bridge, PTP, macvlan |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **GitHub Stars** | 5,243+ | 4,732+ | 31,498+ |
| **Language** | Go | Go | Go |

### The Incus vs LXD Fork Situation

Incus was created in December 2023 when the Linux Containers community forked LXD after Canonical changed the project's governance model. Both share the same codebase at the point of the fork and have diverged since. Incus emphasizes community-driven development under the Linux Containers umbrella, while LXD continues under Canonical's stewardship with enterprise support options.

For most users, the choice between Incus and LXD comes down to **governance philosophy** rather than technical capability — both offer nearly identical features.

## Installation Guide

### Installing Incus

Incus provides packages for major Linux distributions. On Ubuntu/Debian-based systems:

```bash
# Add the Incus repository and install
sudo add-apt-repository ppa:ubuntu-lxc/stable
sudo apt update
sudo apt install incus

# Initialize Incus (interactive setup)
sudo incus admin init

# Add your user to the incus group for non-root access
sudo adduser $USER incus
newgrp incus
```

For Arch Linux users, Incus is available in the official repositories:

```bash
sudo pacman -S incus
sudo systemctl enable --now incus.service incus.socket
```

### Installing LXD

LXD follows a nearly identical installation pattern on Ubuntu:

```bash
# Install via snap (recommended by Canonical)
sudo snap install lxd

# Or via APT on Ubuntu 24.04+
sudo apt install lxd

# Initialize LXD
sudo lxd init

# Add user to the lxd group
sudo adduser $USER lxd
newgrp lxd
```

### Installing Podman

Podman is widely available across distributions and does not require a running daemon:

```bash
# Ubuntu/Debian
sudo apt install podman podman-compose

# Fedora/RHEL
sudo dnf install podman podman-compose

# Arch Linux
sudo pacman -S podman

# Verify installation
podman --version
# podman version 5.x.x
```

## Managing Containers and Virtual Machines

### Incus: Creating and Running System Containers

Incus uses the `incus` CLI (compatible with the `lxc` command syntax):

```bash
# Launch an Ubuntu 24.04 system container
incus launch images:ubuntu/24.04 my-web-server

# List running instances
incus list
# +---------------+---------+---------------------+------+
# |     NAME      |  STATE  |        IPV4         | TYPE |
# +---------------+---------+---------------------+------+
# | my-web-server | RUNNING | 10.0.4.201 (eth0)   | CONTAINER |
# +---------------+---------+---------------------+------+

# Execute a command inside the container
incus exec my-web-server -- apt update && apt install -y nginx

# Create a VM instead of a container
incus launch images:ubuntu/24.04 my-vm --vm --cpu 4 --memory 4GiB

# Set resource limits
incus config set my-web-server limits.cpu 2
incus config set my-web-server limits.memory 2GiB
```

### LXD: Equivalent Commands

LXD's CLI is nearly identical (swap `incus` for `lxc`):

```bash
# Launch a system container
lxc launch images:ubuntu/24.04 my-web-server

# Create a VM with resource limits
lxc launch images:ubuntu/24.04 my-vm --vm \
  --cpu 4 \
  --memory 4GiB

# Set resource limits
lxc config set my-web-server limits.cpu 2
lxc config set my-web-server limits.memory 2GiB
```

### Podman: Running Application Containers

Podman uses Docker-compatible commands and focuses on application-level containers:

```bash
# Run an Nginx container (Docker-compatible syntax)
podman run -d --name web-server \
  -p 8080:80 \
  -v /var/www/html:/usr/share/nginx/html:ro \
  --restart unless-stopped \
  docker.io/library/nginx:latest

# Run rootless (default behavior)
podman run -d --name my-app \
  -p 3000:3000 \
  my-registry/my-app:latest

# List running containers
podman ps

# Generate a systemd unit file for auto-start
podman generate systemd --name web-server --files --restart-policy=always
```

## Networking Configuration

### Incus/LXD Network Setup

Both Incus and LXD share the same networking model. Create managed bridges with DHCP and DNS:

```yaml
# Create a managed bridge network
incus network create br0 \
  ipv4.address=10.0.4.1/24 \
  ipv4.nat=true \
  ipv6.address=none \
  description="Primary container network"

# Attach a container to the network
incus network attach br0 my-web-server eth0

# Set a static IP
incus config device override my-web-server eth0 ipv4.address=10.0.4.100

# Create an OVN network for multi-host setups
incus network set br0 dns.mode=managed
```

### Podman Networking

Podman uses CNI or netavark for container networking:

```bash
# Create a custom network
podman network create my-network

# Run containers on the same network (DNS resolution works)
podman run -d --name db --network my-network postgres:16
podman run -d --name app --network my-network \
  -e DATABASE_HOST=db \
  my-app:latest

# Port mapping with host network
podman run -d --name web \
  -p 80:8080 \
  --network my-network \
  nginx:latest
```

For Podman Compose (Docker Compose equivalent):

```yaml
# docker-compose.yml (compatible with podman-compose)
version: "3.8"
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html:ro
    restart: unless-stopped

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: secure_password
      POSTGRES_DB: myapp
    volumes:
      - pgdata:/var/lib/postgresql/data

volumes:
  pgdata:
```

## Storage Management

### Incus/LXD Storage Pools

Both tools support the same storage drivers with identical configuration:

```bash
# Create a ZFS storage pool
incus storage create pool-zfs zfs \
  source=tank/incus \
  zfs.pool_name=tank/incus

# Create a Btrfs storage pool
incus storage create pool-btrfs btrfs \
  source=/dev/sdb1

# Set the default storage pool
incus storage set pool-zfs volumes.size 20GB

# Use the pool for a new container
incus launch images:ubuntu/24.04 my-app \
  --storage pool-zfs \
  --config limits.disk=50GB
```

### Podman Storage

Podman relies on the host's storage driver configuration, defined in `containers/storage.conf`:

```toml
# /etc/containers/storage.conf
[storage]
driver = "overlay"

[storage.options.overlay]
mount_program = "/usr/bin/fuse-overlayfs"

[storage.options]
# Pull images from multiple registries
registries = [
  "docker.io",
  "quay.io",
  "ghcr.io"
]
```

## Clustering and High Availability

### Incus Clustering

Incus supports native clustering using a RAFT-based consensus protocol:

```bash
# Bootstrap the first cluster node
incus admin init --cluster

# Join additional nodes
incus admin init --cluster \
  --cluster-token <token-from-first-node>

# Create a clustered network (spans all nodes)
incus network create ovn-net \
  --type ovn \
  network=br0

# Schedule containers on specific nodes
incus launch images:ubuntu/24.04 app1 \
  --target node02
```

### LXD Clustering

LXD uses dqlite for distributed consensus:

```bash
# Bootstrap cluster
lxd init --cluster

# Join additional nodes
lxd init --cluster \
  --cluster-certificate <cert> \
  --cluster-token <token>
```

### Podman: External Orchestration Required

Podman does not have built-in clustering. For multi-host deployments, you need:

- **Kubernetes** (with CRI-O or containerd) — full orchestration
- **Podman Quadlet** — systemd-based single-host management
- **Nomad** or **Swarm** — external cluster managers

For simple multi-container setups on a single host, Podman Compose or Quadlet systemd units handle most use cases:

```ini
# /etc/containers/systemd/web.container
[Container]
Image=docker.io/library/nginx:latest
PublishPort=8080:80
Volume=/var/www/html:/usr/share/nginx/html:ro

[Install]
WantedBy=default.target
```

## Security Comparison

| Security Feature | Incus | LXD | Podman |
|-----------------|-------|-----|--------|
| **User namespaces** | ✅ Yes | ✅ Yes | ✅ Yes (default) |
| **Seccomp profiles** | ✅ Customizable | ✅ Customizable | ✅ Default + custom |
| **AppArmor/SELinux** | ✅ Both | ✅ Both | ✅ Both |
| **Rootless containers** | Partial | Partial | ✅ Full support |
| **Image signing** | ✅ Yes | ✅ Yes | ✅ Sigstore/cosign |
| **RBAC** | ✅ Project-based | ✅ Project-based | ❌ None (use systemd) |
| **Audit logging** | ✅ Built-in | ✅ Built-in | ❌ Via journald |

## When to Choose Each Platform

### Choose Incus when:
- You want the community-driven fork with faster iteration
- You need system containers AND virtual machines on the same platform
- You value the Linux Containers project governance model
- You're building a homelab or small cluster

### Choose LXD when:
- You want Canonical-backed enterprise support
- You're already in the Ubuntu/Canonical ecosystem
- You need commercial SLA guarantees
- You prefer a more conservative release cycle

### Choose Podman when:
- You need Docker-compatible application containers
- Rootless execution is a requirement (shared hosting, multi-tenant)
- You don't want to run a background daemon
- You're migrating from Docker and want drop-in compatibility
- You need CI/CD integration (GitHub Actions, GitLab CI)

## Migration Paths

### Docker to Podman

Podman provides a compatibility layer that makes migration nearly transparent:

```bash
# Install the Docker-compatible alias
sudo apt install podman-docker

# Docker commands now work with Podman backend
docker run hello-world  # Actually runs podman run

# Migrate existing containers
podman load -i backup.tar
podman images
```

### LXD to Incus

Since Incus is a fork of LXD, migration is straightforward:

```bash
# Stop LXD
sudo systemctl stop lxd

# Install Incus
sudo apt install incus

# Migrate the database and storage
sudo incus admin migrate

# Verify all instances migrated
incus list
```

For related reading on container security, see our [container image scanning guide](../2026-04-24-self-hosted-container-image-scanning-trivy-grype-clair-anchore-guide/) and [Kubernetes hardening comparison](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/). If you're evaluating full virtualization platforms instead, our [Proxmox vs XCP-ng comparison](../proxmox-ve-vs-xcp-ng-vs-ovirt-self-hosted-virtualization-guide-2026/) covers the VM-centric alternatives.

## FAQ

### Is Incus better than LXD for self-hosting?

It depends on your priorities. Incus is community-driven and tends to adopt new features faster, while LXD benefits from Canonical's enterprise support and longer testing cycles. Technically, they are nearly identical since they share the same codebase at the fork point. For personal homelabs, Incus is often preferred due to community governance. For enterprise deployments requiring vendor support, LXD may be the better choice.

### Can Podman replace Docker entirely?

For most use cases, yes. Podman is drop-in compatible with Docker CLI commands, supports Docker Compose files (via podman-compose), and can run any Docker image from any registry. The main differences are that Podman is daemonless (no background service required) and supports rootless containers by default. The only gap is Docker Swarm orchestration, which Podman does not support natively.

### Do Incus and LXD support Docker images?

Yes, both Incus and LXD can run OCI (Docker-format) images alongside their native system container images. Use the `oci:` prefix to pull Docker images:

```bash
incus launch oci:nginx my-nginx
```

However, for pure Docker container workloads, Podman provides a more natural experience with full Docker Compose compatibility.

### Can I run both Incus/LXD and Podman on the same server?

Absolutely. They operate at different layers — Incus/LXD manages system containers and VMs, while Podman manages application containers. Many self-hosted setups use Incus/LXD for the base infrastructure (databases, message brokers as system containers) and Podman for ephemeral application workloads.

### How does clustering work with Incus?

Incus uses a RAFT-based consensus protocol for clustering. You designate one or more nodes as database members, and the cluster elects a leader automatically. Containers can be scheduled on any node, and the shared storage (via Ceph, NFS, or replicated ZFS) ensures data availability. Incus also supports OVN networking across cluster nodes for automatic container-to-container routing.

### What is the resource overhead of system containers vs VMs?

System containers (Incus/LXD) share the host kernel, so overhead is minimal — typically 2-5% CPU and near-zero memory overhead beyond what the workload itself consumes. Virtual machines (also supported by Incus/LXD via QEMU/KVM) have higher overhead — roughly 10-20% CPU plus dedicated memory allocation. Application containers (Podman) have overhead similar to system containers since they also use kernel-level namespaces.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Incus vs LXD vs Podman: Self-Hosted Container & System Virtualization Guide 2026",
  "description": "Compare Incus, LXD, and Podman for self-hosted container and system virtualization. Complete guide to installation, configuration, networking, and migration.",
  "datePublished": "2026-04-24",
  "dateModified": "2026-04-24",
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
