---
title: "Self-Hosted Container Checkpoint & Restore: CRIU, Podman Checkpoint, and Kubernetes Migration Guide 2026"
date: 2026-05-04T11:00:00+00:00
tags: ["containers", "checkpoint-restore", "criu", "podman", "kubernetes", "container-migration", "docker"]
draft: false
---

Container checkpoint and restore is the ability to **save the complete runtime state** of a running container — memory, file descriptors, network connections, process state — to disk, then restore it later on the same or a different host. This capability enables live migration, zero-downtime updates, and stateful container recovery that traditional container restarts cannot achieve.

The technology behind this is **CRIU** (Checkpoint/Restore in Userspace), a Linux kernel feature that has matured significantly and now supports most major container runtimes.

## What Is Container Checkpoint & Restore?

When you checkpoint a container, the system captures:
- **Process memory** — all RAM pages for running processes
- **Open file descriptors** — sockets, pipes, file handles
- **Network state** — TCP connections, listening ports
- **Process tree** — parent-child relationships, PID mapping
- **Mount namespaces** — filesystem mount points and state

When restored, the container resumes exactly where it left off — including established TCP connections, in-memory caches, and running computations. This is fundamentally different from `docker stop && docker start`, which terminates the process and loses all runtime state.

## CRIU — The Foundation

[CRIU](https://github.com/checkpoint-restore/criu) is the core Linux technology that enables checkpoint/restore in userspace. With 3,800+ GitHub stars, it is the foundation for all container-level checkpoint/restore implementations.

**Key Features:**
- Checkpoint and restore of entire process trees
- Network connection migration (TCP state preservation)
- File descriptor migration (open files, pipes, sockets)
- Namespace support (PID, mount, network, IPC)
- Lazy pages support (page in memory on demand during restore)
- User namespace support for rootless containers

**Installation:**

```bash
# Ubuntu/Debian
sudo apt install criu

# RHEL/CentOS/Fedora
sudo dnf install criu

# Alpine
sudo apk add criu
```

**Basic Usage:**

```bash
# Checkpoint a process (by PID)
sudo criu dump -t <PID> -D /tmp/checkpoint --tcp-established --shell-job

# Restore the process
sudo criu restore -D /tmp/checkpoint --tcp-established --shell-job

# Live migration to another host
sudo criu dump -t <PID> -D /tmp/checkpoint --tcp-established
scp -r /tmp/checkpoint remote:/tmp/
ssh remote "criu restore -D /tmp/checkpoint --tcp-established"
```

**Docker Compose Setup for CRIU:**

```yaml
version: "3.8"
services:
  checkpoint-manager:
    image: ubuntu:24.04
    privileged: true
    volumes:
      - /tmp/checkpoints:/checkpoints
      - /proc:/proc
    cap_add:
      - SYS_ADMIN
      - SYS_PTRACE
    command: >
      bash -c "apt update && apt install -y criu &&
               tail -f /dev/null"
    networks:
      - migration-network

networks:
  migration-network:
    driver: bridge
```

## Podman Checkpoint & Restore

Podman has built-in support for CRIU-based checkpoint and restore, making it the easiest container runtime to use for this workflow. Since Podman runs rootless by default, it also supports rootless checkpoint/restore.

**Installation:**

```bash
# Ubuntu/Debian
sudo apt install podman criu

# RHEL/Fedora
sudo dnf install podman criu
```

**Usage:**

```bash
# Start a container
podman run -d --name myapp nginx:latest

# Checkpoint the running container
podman container checkpoint myapp -e /tmp/myapp-checkpoint.tar.gz

# The container is now stopped, state saved to tarball

# Restore on the same host
podman container restore myapp -i /tmp/myapp-checkpoint.tar.gz

# Or restore on a different host
scp /tmp/myapp-checkpoint.tar.gz remote:/tmp/
ssh remote "podman container restore myapp -i /tmp/myapp-checkpoint.tar.gz"
```

**Docker Compose Alternative (Podman Compose):**

```yaml
version: "3.8"
services:
  webapp:
    image: nginx:latest
    ports:
      - "8080:80"
    volumes:
      - ./html:/usr/share/nginx/html
  backup-service:
    image: ubuntu:24.04
    privileged: true
    volumes:
      - /var/lib/containers/storage:/var/lib/containers/storage
      - ./checkpoints:/checkpoints
    command: >
      bash -c "apt update && apt install -y criu &&
               podman container checkpoint webapp -e /checkpoints/webapp.tar.gz"
```

## Kubernetes Container Migration

While Kubernetes does not natively support container checkpoint/restore, several projects enable live migration of pods between nodes:

### Kube-CRIU Integration

The `cri` (Container Runtime Interface) supports checkpoint/restore operations through the CRI API. Some runtime implementations provide this functionality:

```yaml
# Pod manifest with checkpoint annotation
apiVersion: v1
kind: Pod
metadata:
  name: migratable-pod
  annotations:
    checkpoint.kubernetes.io/enabled: "true"
spec:
  containers:
    - name: app
      image: myapp:latest
      resources:
        requests:
          memory: "256Mi"
          cpu: "250m"
```

**Using crictl for Checkpoint:**

```bash
# Get the container ID
crictl ps --name myapp

# Checkpoint the container
crictl checkpoint <container-id> /tmp/checkpoint.tar

# On target node, restore
crictl restore <new-container-id> /tmp/checkpoint.tar
```

### KubeVirt Live Migration

For VM-based workloads, [KubeVirt](https://github.com/kubevirt/kubevirt) provides native live migration between Kubernetes nodes, which is often a more practical approach for production stateful workloads:

```yaml
apiVersion: kubevirt.io/v1
kind: VirtualMachine
metadata:
  name: migratable-vm
spec:
  running: true
  template:
    spec:
      domain:
        resources:
          requests:
            memory: 2Gi
        devices:
          disks:
            - name: rootfs
              disk:
                bus: virtio
      volumes:
        - name: rootfs
          persistentVolumeClaim:
            claimName: vm-rootfs
```

**Trigger Migration:**

```bash
# Create a VirtualMachineInstanceMigration resource
kubectl apply -f - <<EOF
apiVersion: kubevirt.io/v1
kind: VirtualMachineInstanceMigration
metadata:
  name: vm-migration
spec:
  vmiName: migratable-vm
EOF

# Monitor migration status
kubectl get vmi_migration vm-migration
```

## Comparison Table

| Feature | CRIU (Direct) | Podman Checkpoint | KubeVirt Migration |
|---------|--------------|-------------------|-------------------|
| Checkpoint Target | Processes | Containers | Virtual Machines |
| Restore Location | Same or different host | Same or different host | Different K8s node |
| TCP State Preservation | ✅ Yes | ✅ Yes | ✅ Yes |
| File Descriptor Migration | ✅ Yes | ✅ Yes | ✅ Yes |
| Rootless Support | ✅ (with user ns) | ✅ Yes | N/A (VM-level) |
| Orchestration Integration | Manual | Podman Compose | Kubernetes native |
| Live Migration | Manual (dump + copy + restore) | Manual (tar + copy + restore) | ✅ Zero-downtime |
| Setup Complexity | High | Low | Medium |
| Production Ready | ✅ Yes | ✅ Yes | ✅ Yes |
| GitHub Stars | 3,800+ | 31,500+ (Podman) | 17,000+ (KubeVirt) |
| Last Updated | April 2026 | May 2026 | May 2026 |

## Use Cases

### Zero-Downtime Container Updates

Instead of stopping a container and starting a new version (losing in-memory state), checkpoint the running container, start the new version, and restore the old container's state into a sidecar for debugging:

```bash
# Checkpoint current version
podman container checkpoint myapp -e /tmp/myapp-v1.tar.gz

# Start new version
podman run -d --name myapp-v2 myapp:v2

# Restore v1 state for comparison/debugging
podman run -d --name myapp-v1-debug --restore /tmp/myapp-v1.tar.gz myapp:v1
```

### Disaster Recovery

Save container state regularly as a backup strategy. If a node fails, restore the checkpoint on a healthy node:

```bash
# Cron job for regular checkpoints
0 */6 * * * podman container checkpoint myapp -e /backup/myapp-$(date +\%F-\%H).tar.gz
```

### Cross-Datacenter Migration

Migrate workloads between datacenters by checkpointing on the source, transferring the checkpoint archive, and restoring on the destination — preserving all active connections and in-memory state.

## Why Container Checkpoint Matters

Traditional container orchestration treats containers as ephemeral and stateless. When you need to move a container, you stop it and start a fresh instance — losing all runtime state. Checkpoint and restore changes this paradigm:

- **Preserves TCP connections** — clients don't see connection drops during migration
- **Maintains in-memory caches** — no cold-start performance penalty after restore
- **Enables live migration** — move workloads between hosts without downtime
- **Simplifies debugging** — save a failing container's exact state for offline analysis

For container runtime comparisons, see our [containerd vs CRI-O vs Podman guide](../containerd-vs-cri-o-vs-podman-self-hosted-container-runtimes/) and [Incus vs LXD vs Podman comparison](../2026-04-24-incus-vs-lxd-vs-podman-self-hosted-container-virtualization-guide-2026/). For container sandboxing approaches that complement checkpoint/restore security, check our [gVisor vs Kata Containers guide](../2026-04-20-gvisor-vs-kata-containers-vs-firecracker-container-sandboxing-guide-2026/).

## FAQ

### What is the difference between checkpoint and snapshot?

A **snapshot** captures the filesystem state of a container at a point in time (like `docker commit`). A **checkpoint** captures the complete runtime state — memory, network connections, file descriptors, and process state. Snapshots let you restart from a filesystem baseline; checkpoints let you resume exactly where the container left off, including active network connections.

### Does Docker support checkpoint and restore?

Docker added experimental checkpoint/restore support using CRIU in version 1.13, but it was never promoted to stable and was deprecated in later versions. Podman has better native support. For Docker-based workflows, you need to use CRIU directly or switch to Podman.

### What are the limitations of container checkpoint/restore?

Not all applications can be checkpointed. Limitations include: applications with open GPU contexts, some database engines with memory-mapped files, containers with mounted FUSE filesystems, and applications using certain Linux kernel features (userfaultfd, inotify). CRIU provides a pre-check (`criu check`) to verify compatibility before attempting checkpoint.

### Can I checkpoint a running database?

Technically yes, but it is risky. Databases like PostgreSQL and MySQL use memory-mapped files and transaction logs. Checkpointing a running database may result in inconsistent state on restore. It is safer to use the database's native backup tools (pg_dump, mysqldump) combined with WAL/archive logs for consistent backups.

### How large is a checkpoint file?

Checkpoint size depends on the container's memory usage. A container using 512MB of RAM will produce a checkpoint of roughly 200-500MB (compressed). With lazy pages support, you can restore without immediately loading all memory pages, reducing restore time significantly.

### Is container checkpoint/restore production-ready?

CRIU and Podman checkpoint are production-ready for supported workloads. Kubernetes-native migration is still emerging — KubeVirt provides the most mature solution for VM workloads, while container-level migration in Kubernetes requires manual orchestration or custom operators. Always test checkpoint/restore with your specific application before relying on it in production.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Container Checkpoint & Restore: CRIU, Podman Checkpoint, and Kubernetes Migration Guide 2026",
  "description": "Guide to container checkpoint and restore using CRIU, Podman, and KubeVirt. Learn how to save container runtime state, migrate between hosts, and achieve zero-downtime container migration.",
  "datePublished": "2026-05-04",
  "dateModified": "2026-05-04",
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
