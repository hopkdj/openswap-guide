---
title: "NFS-Ganesha vs UNFS3 vs Kernel NFS: Self-Hosted NFS Server Guide 2026"
date: 2026-04-30
tags: ["comparison", "guide", "self-hosted", "nfs", "file-server", "storage"]
draft: false
description: "Compare NFS-Ganesha, UNFS3, and kernel NFS (nfsd) for self-hosted file sharing. Detailed setup guides with Docker Compose configs, performance benchmarks, and deployment recommendations for 2026."
---

Network File System (NFS) remains one of the most widely used protocols for network file sharing on Linux and UNIX systems. Whether you're serving build artifacts to CI/CD runners, sharing media libraries across homelab nodes, or providing storage for Kubernetes PersistentVolumes, choosing the right NFS server implementation matters for performance, security, and operational simplicity.

This guide compares three self-hosted NFS server options: **NFS-Ganesha** (user-space, feature-rich), **UNFS3** (lightweight NFSv3-only), and the **Kernel NFS Server** (nfsd, built into Linux). We'll cover architecture differences, Docker deployment, configuration examples, and help you pick the right tool for your use case.

For a broader comparison of self-hosted file sharing protocols including SMB/CIFS and WebDAV, see our [Samba vs NFS vs WebDAV guide](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide-2026/).

## Why Self-Host an NFS Server?

NFS provides native POSIX-compliant file sharing with near-local disk performance. Unlike object storage (S3) or block storage (iSCSI), NFS lets applications read and write files using standard system calls — no special SDKs or mounting protocols required.

Key advantages of self-hosting your own NFS server:

- **Zero licensing costs** — all three options are fully open source
- **Full data sovereignty** — files never leave your infrastructure
- **Native POSIX semantics** — file locking, permissions, and extended attributes work correctly
- **Wide client support** — Linux, macOS, BSD, and Windows (with NFS client enabled) all connect natively
- **Low overhead** — NFS runs over TCP with minimal protocol overhead compared to HTTP-based alternatives

For distributed file system needs spanning multiple nodes, check out our [JuiceFS vs Alluxio vs CephFS comparison](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/).

## Architecture Comparison

### NFS-Ganesha: User-Space Feature-Rich Server

[NFS-Ganesha](https://github.com/nfs-ganesha/nfs-ganesha) is an NFSv3, v4, and v4.1 file server that runs entirely in user space. With **1,749 GitHub stars** and active development (last updated April 2026), it's the most feature-complete open source NFS server available.

Key architectural features:

- Runs as a standard userspace process — no kernel module dependencies
- Pluggable backend architecture (FSAL — File System Abstraction Layer) supporting local filesystems, Ceph, CephFS, GLUSTER, CEPH, and more
- Full NFSv4.1 support including pNFS (parallel NFS) for performance scaling
- Built-in Kerberos authentication (krb5, krb5i, krb5p)
- Dynamic export configuration — add/remove shares without restarting
- Multi-threaded I/O with configurable thread pools

### UNFS3: Lightweight NFSv3 Server

[UNFS3](https://github.com/unfs3/unfs3) is a user-space implementation of the NFSv3 specification. At **155 stars**, it's a smaller project but serves a specific niche: minimal, easy-to-deploy NFSv3 sharing.

Key characteristics:

- Implements only NFSv3 — no NFSv4 features (no Kerberos, no pNFS)
- Runs entirely in user space with minimal dependencies
- Single binary deployment — simple to install and configure
- Suitable for basic file sharing where NFSv4 features aren't needed
- Limited to TCP transport (no UDP)

### Kernel NFS Server (nfsd): Built Into Linux

The kernel NFS server (`nfsd`) has been part of the Linux kernel since version 1.0. It's the most battle-tested NFS implementation, powering everything from home NAS boxes to enterprise storage arrays.

Key characteristics:

- Runs in kernel space — maximum performance, zero context switching overhead
- Supports NFSv2, v3, v4, v4.1, and v4.2
- Managed via the `nfs-kernel-server` package on Debian/Ubuntu or `nfs-utils` on RHEL/CentOS
- Tightly integrated with the kernel VFS layer for optimal performance
- Configuration via `/etc/exports` — simple but requires service restart for changes

## Feature Comparison Table

| Feature | NFS-Ganesha | UNFS3 | Kernel NFS (nfsd) |
|---------|-------------|-------|-------------------|
| **NFS Versions** | v3, v4.0, v4.1 | v3 only | v2, v3, v4.0, v4.1, v4.2 |
| **Execution Mode** | User-space | User-space | Kernel-space |
| **Kerberos Auth** | Yes (krb5/krb5i/krb5p) | No | Yes |
| **pNFS Support** | Yes | No | Yes (v4.1+) |
| **Dynamic Exports** | Yes (DBUS/API) | No | No (requires restart) |
| **Pluggable Backends** | Yes (FSAL: POSIX, CEPH, GLUSTER, CEPH) | No (POSIX only) | No (kernel VFS only) |
| **NFSv4 Delegations** | Yes | N/A | Yes |
| **TCP Wrappers** | Yes | Yes | Yes |
| **NLM (Lock Manager)** | Yes | Yes | Yes |
| **Docker Friendly** | Excellent | Good | Limited (requires privileged) |
| **GitHub Stars** | 1,749 | 155 | In-kernel |
| **Last Active** | April 2026 | July 2025 | Always updated with kernel |

## Installation & Configuration

### NFS-Ganesha: Docker Compose Deployment

NFS-Ganesha deploys cleanly in Docker because it runs in user space. Here's a production-ready `docker-compose.yml`:

```yaml
version: "3.8"

services:
  nfs-ganesha:
    image: apnar/nfs-ganesha:latest
    container_name: nfs-ganesha
    privileged: true
    cap_add:
      - SYS_ADMIN
      - DAC_READ_SEARCH
    ports:
      - "2049:2049/tcp"    # NFS
      - "111:111/tcp"      # Portmapper
      - "111:111/udp"      # Portmapper (UDP)
      - "662:662/tcp"      # MNT
      - "662:662/udp"      # MNT (UDP)
      - "32803:32803/tcp"  # MOUNTD
      - "32769:32769/udp"  # MOUNTD (UDP)
    volumes:
      - ./ganesha.conf:/etc/ganesha/ganesha.conf:ro
      - /srv/nfs:/srv/nfs:rw
      - /var/lib/nfs:/var/lib/nfs:rw
    restart: unless-stopped
    networks:
      - storage-net

networks:
  storage-net:
    driver: bridge
```

Create `ganesha.conf` for the export configuration:

```conf
# /etc/ganesha/ganesha.conf
NFS_CORE_PARAM {
    Enable_NFSv3 = true;
    Enable_NFSv4 = true;
    NFS_Port = 2049;
}

MNT_PARAM {
    Enable_MNT = true;
    MNT_Port = 662;
}

NLM_PARAM {
    Enable_NLM = true;
    NLM_Port = 32803;
}

EXPORT {
    Export_ID = 100;
    Path = /srv/nfs/data;
    Pseudo = /data;
    Access_Type = RW;
    Protocols = 3, 4;
    Transports = TCP;
    SecType = sys;
    Squash = No_Root_Squash;

    FSAL {
        Name = POSIX;
    }
}

EXPORT {
    Export_ID = 101;
    Path = /srv/nfs/shared;
    Pseudo = /shared;
    Access_Type = RW;
    Protocols = 3, 4;
    Transports = TCP;
    SecType = sys;
    Squash = Root_Squash;

    FSAL {
        Name = POSIX;
    }
}

LOG {
    Facility {
        name = FILE;
        destination = "/var/log/ganesha/ganesha.log";
        enable = active;
    }
}
```

Start the server and verify:

```bash
docker compose up -d
docker compose logs -f nfs-ganesha

# Verify from a client
showmount -e <server-ip>
mount -t nfs <server-ip>:/data /mnt/nfs
```

### UNFS3: Docker Compose Deployment

UNFS3 is simpler to deploy but limited to NFSv3. Here's a working compose configuration:

```yaml
version: "3.8"

services:
  unfs3:
    image: ghcr.io/fuz/unfs3:latest
    container_name: unfs3
    privileged: true
    cap_add:
      - SYS_ADMIN
    ports:
      - "2049:2049/tcp"
      - "111:111/tcp"
      - "111:111/udp"
      - "892:892/tcp"
      - "892:892/udp"
    volumes:
      - ./exports:/etc/exports:ro
      - /srv/nfs:/srv/nfs:rw
    restart: unless-stopped
    networks:
      - storage-net

networks:
  storage-net:
    driver: bridge
```

The exports file format is identical to the standard `/etc/exports`:

```conf
# /etc/exports for UNFS3
/srv/nfs/data 192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash)
/srv/nfs/shared 192.168.1.0/24(ro,sync,no_subtree_check)
```

```bash
docker compose up -d

# Verify
showmount -e <server-ip>
mount -t nfs -o vers=3 <server-ip>:/srv/nfs/data /mnt/nfs
```

### Kernel NFS Server: Native Installation

The kernel NFS server cannot run cleanly inside an unprivileged Docker container because it requires kernel module access. The recommended deployment is native on the host:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y nfs-kernel-server

# RHEL/CentOS/Fedora
sudo dnf install -y nfs-utils

# Create export directories
sudo mkdir -p /srv/nfs/{data,shared}
sudo chown -R nobody:nogroup /srv/nfs
sudo chmod -R 777 /srv/nfs
```

Configure exports in `/etc/exports`:

```conf
# /etc/exports - Kernel NFS server
/srv/nfs/data  192.168.1.0/24(rw,sync,no_subtree_check,no_root_squash,sec=sys)
/srv/nfs/shared 192.168.1.0/24(ro,sync,no_subtree_check,sec=sys)
192.168.1.100(rw,sync,no_root_squash,no_subtree_check)
```

Apply and start:

```bash
sudo exportfs -ra          # Re-read exports without restart
sudo exportfs -v           # Verify active exports
sudo systemctl enable --now nfs-server
sudo systemctl status nfs-server
```

For clients to connect:

```bash
# Show available exports
showmount -e <server-ip>

# Mount NFS share
sudo mount -t nfs <server-ip>:/srv/nfs/data /mnt/nfs

# Mount with NFSv4 only
sudo mount -t nfs4 <server-ip>:/srv/nfs/data /mnt/nfs

# Persistent mount via /etc/fstab
echo '<server-ip>:/srv/nfs/data /mnt/nfs nfs defaults,_netdev 0 0' | sudo tee -a /etc/fstab
```

## Performance Considerations

### Kernel NFS: Maximum Throughput

Running in kernel space means nfsd avoids context switching between user and kernel mode for every I/O operation. For high-throughput workloads (video editing, database backups, large file transfers), the kernel server delivers the best raw performance.

### NFS-Ganesha: Competitive With Tuning

NFS-Ganesha's user-space design adds some overhead, but configurable thread pools and the FSAL architecture let you optimize for specific workloads. For most homelab and small-business workloads, the performance difference is negligible (< 5%).

Key tuning parameters in `ganesha.conf`:

```conf
NFS_CORE_PARAM {
    Nb_Grace = 90;
    Lease_Lifetime = 60;
    NFS_Port = 2049;
    Bind_Addr = "0.0.0.0";
}

CACHEINODE {
    Entries_HWMark = 100000;
    Parts = 128;
    Cache_Size = 1000000;
}
```

### UNFS3: Adequate for Light Workloads

UNFS3 is not optimized for high throughput. It handles basic file sharing well but should not be used for performance-critical workloads like database storage or video editing NAS.

## Security Best Practices

All three NFS servers support the following security hardening measures:

**1. Restrict exports to specific subnets** — never use `*` in export definitions:

```conf
# BAD — allows any client
/srv/nfs *(rw,sync)

# GOOD — restrict to your network
/srv/nfs 192.168.1.0/24(rw,sync,no_root_squash)
```

**2. Use `root_squash` to prevent root access on the server:**

```conf
/srv/nfs/shared 192.168.1.0/24(rw,sync,root_squash,no_subtree_check)
```

**3. Enable Kerberos authentication** (NFS-Ganesha and kernel NFS only):

```conf
# NFS-Ganesha config
EXPORT {
    Export_ID = 100;
    SecType = krb5;  # or krb5i for integrity, krb5p for privacy
    ...
}
```

**4. Use TCP-only transport** — disable UDP to prevent spoofing attacks:

```conf
# Kernel NFS — edit /etc/nfs.conf
[nfsd]
tcp=y
udp=n
```

**5. Firewall the NFS ports:**

```bash
sudo ufw allow from 192.168.1.0/24 to any port 2049 proto tcp
sudo ufw allow from 192.168.1.0/24 to any port 111 proto tcp
```

For a comprehensive self-hosted firewall guide, see our [UFW vs firewalld vs iptables comparison](../self-hosted-firewall-ufw-firewalld-iptables/).

## When to Choose Which Server

| Scenario | Recommendation | Rationale |
|----------|---------------|-----------|
| **Kubernetes PersistentVolumes** | NFS-Ganesha | NFSv4.1 + pNFS, dynamic exports, container-native |
| **Homelab media sharing** | Kernel NFS (nfsd) | Maximum throughput, zero overhead, proven reliability |
| **Quick NFSv3 file share** | UNFS3 | Single binary, minimal config, no kernel dependencies |
| **Ceph backend storage** | NFS-Ganesha | Native CEPH FSAL — no kernel Ceph client needed |
| **Enterprise with Kerberos** | NFS-Ganesha or Kernel NFS | Both support krb5/krb5i/krb5p |
| **High-performance video editing NAS** | Kernel NFS (nfsd) | Lowest latency, no context switching overhead |
| **Docker container deployment** | NFS-Ganesha | Clean user-space architecture, no privileged mode needed |

## Troubleshooting

### Common NFS Client Errors

**"mount.nfs: access denied by server"** — Check that the client IP matches an export rule and the `exports` file has been reloaded (`exportfs -ra` for kernel, restart for Ganesha/UNFS3).

**"Stale file handle"** — The server-side file was modified outside NFS (e.g., directly on the server filesystem). Remount the share:

```bash
sudo umount -f /mnt/nfs
sudo mount -t nfs <server-ip>:/path /mnt/nfs
```

**"Permission denied" despite RW export** — Check `root_squash` is set correctly and file permissions on the server allow the mapped UID/GID:

```bash
ls -la /srv/nfs/data/
id  # Check client UID/GID matches server permissions
```

### Debugging NFS-Ganesha

```bash
docker compose exec nfs-ganesha cat /var/log/ganesha/ganesha.log

# Increase log level in ganesha.conf
LOG {
    Facility {
        name = FILE;
        destination = "/var/log/ganesha/ganesha.log";
        enable = active;
    }
    Components {
        ALL = EVENT_DEBUG;
    }
}
```

### Debugging Kernel NFS

```bash
# Check nfsd threads
cat /proc/fs/nfsd/threads

# Check active NFS connections
cat /proc/fs/nfsd/pool_stats

# Increase kernel NFS debug
echo 32767 > /proc/sys/sunrpc/nfsd_debug
```

## FAQ

### What is the difference between NFSv3 and NFSv4?

NFSv4 introduced several major improvements over NFSv3: integrated file locking (no separate NLM protocol), stateful protocol with better recovery, built-in security (Kerberos), compound operations for reduced latency, and pNFS for parallel data access. NFSv3 remains popular for its simplicity and wide client support, but NFSv4 is recommended for new deployments.

### Can I run NFS inside a Docker container?

Yes, but with caveats. NFS-Ganesha runs cleanly in Docker because it operates in user space — you only need `SYS_ADMIN` and `DAC_READ_SEARCH` capabilities. UNFS3 also works well. The kernel NFS server (nfsd) requires loading kernel modules (`nfsd`, `lockd`, `sunrpc`), which means running with `--privileged` or on the host directly. For container-native deployments, NFS-Ganesha is the best choice.

### Is NFS secure for use over the internet?

NFS was designed for trusted local networks and should **never** be exposed directly to the internet. Always restrict NFS to private networks using firewall rules and export restrictions. For cross-network file sharing, use an SSH tunnel, WireGuard VPN, or a higher-level protocol like SFTP or WebDAV. See our [WireGuard VPN guide](../self-hosted-vpn-wireguard-tailscale-headscale-guide-2026/) for setting up secure network tunnels.

### How do I back up an NFS share?

Since NFS exports are backed by a local filesystem on the server, use standard backup tools on the server side — not from NFS clients. Tools like `rsync`, `restic`, or `borgbackup` should run directly on the NFS server machine accessing the underlying filesystem. This ensures consistent snapshots and avoids network transfer overhead during backup.

### What port does NFS use and do I need to open firewall rules?

NFS primarily uses TCP port **2049**. Additional ports include: **111** (portmapper/rpcbind, TCP+UDP), **662** (MNT/Mountd, TCP+UDP), and **32769/32803** (legacy mountd). For NFSv4-only deployments, you only need port 2049 (TCP) open — NFSv4 eliminates the need for portmapper and mountd. For NFSv3, all the above ports must be accessible between client and server.

### Can NFS-Ganesha use Ceph or other distributed storage as a backend?

Yes. NFS-Ganesha's FSAL (File System Abstraction Layer) supports multiple backends: POSIX (local filesystem), CEPH (Ceph RBD), CEPH_FS (CephFS), GLUSTER, CEPH_RGW (Ceph object gateway), MEM (in-memory), and more. This makes it ideal for serving NFS exports backed by distributed storage without requiring kernel Ceph clients on the NFS server host.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "NFS-Ganesha vs UNFS3 vs Kernel NFS: Self-Hosted NFS Server Guide 2026",
  "description": "Compare NFS-Ganesha, UNFS3, and kernel NFS (nfsd) for self-hosted file sharing. Detailed setup guides with Docker Compose configs, performance benchmarks, and deployment recommendations for 2026.",
  "datePublished": "2026-04-30",
  "dateModified": "2026-04-30",
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
