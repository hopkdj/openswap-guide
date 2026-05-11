---
title: "Self-Hosted NFS High Availability: DRBD vs GlusterFS Geo-Replication vs Pacemaker"
date: "2026-05-11"
tags: ["nfs", "storage", "high-availability", "networking", "self-hosted"]
draft: false
---

Network File System (NFS) remains one of the most widely used protocols for shared storage in enterprise and self-hosted environments. But a single NFS server is a single point of failure — when it goes down, every client loses access to shared data simultaneously. This guide compares three approaches to NFS high availability: DRBD block-level replication, GlusterFS geo-replication, and Pacemaker cluster management with floating IPs.

## The NFS Availability Challenge

NFS clients mount remote filesystems using persistent connections. When the NFS server becomes unreachable, client applications hang (often indefinitely) waiting for I/O operations to complete. Unlike stateless protocols like HTTP, NFS sessions are stateful — reconnecting requires unmounting and remounting, which is not automatic on most systems. High availability for NFS means maintaining both data replication and a consistent network identity (IP address) that clients can reconnect to.

| Feature | DRBD + NFS | GlusterFS Geo-Replication | Pacemaker HA NFS |
|---------|-----------|--------------------------|-----------------|
| **Replication Level** | Block (synchronous) | File (asynchronous) | Shared storage or block |
| **Failover Time** | 10-30 seconds | Minutes (async delay) | 10-60 seconds |
| **Data Loss Risk** | Zero (sync mode) | Small (async lag) | Depends on backend |
| **Active-Active** | No (active-passive) | Yes (both writable) | No (active-passive) |
| **Cross-Site Support** | Yes (with async mode) | Yes (designed for it) | Yes (with shared storage) |
| **Bandwidth Usage** | All block changes | Changed files only | N/A (shared storage) |
| **Split-Brain Protection** | Built-in (fencing) | Manual resolution | STONITH fencing |
| **Complexity** | Moderate | High | High |
| **Docker Deployment** | Possible (privileged) | Possible (privileged) | Not recommended in containers |

## DRBD + NFS: Block-Level Synchronous Replication

Distributed Replicated Block Device (DRBD) mirrors block devices between two servers at the kernel level. Combined with NFS, it provides synchronous replication with zero data loss in the event of a primary server failure.

### Architecture

```
  Client → Virtual IP (192.168.1.100)
                ↓
        ┌───────────────┐
        │  DRBD Primary  │ ← NFS Server (exports /data)
        │  /dev/drbd0    │
        └───────┬───────┘
                │ (synchronous TCP replication)
        ┌───────┴───────┐
        │ DRBD Secondary │ ← Standby NFS (not running)
        │ /dev/drbd0     │
        └───────────────┘
```

### Deployment with Docker Compose

```yaml
version: "3.8"
services:
  nfs-server:
    image: itsthenetwork/nfs-server-alpine:latest
    container_name: nfs-primary
    privileged: true
    cap_add:
      - SYS_ADMIN
      - NET_ADMIN
    environment:
      SHARED_DIRECTORY: /data
    volumes:
      - drbd-data:/data
      - /dev:/dev
    ports:
      - "2049:2049"
      - "111:111"
      - "111:111/udp"
    restart: unless-stopped

volumes:
  drbd-data:
    driver: local
    driver_opts:
      type: none
      device: /dev/drbd0
      o: bind
```

### DRBD Configuration

```
global {
    usage-count no;
}

common {
    protocol C;  # Synchronous replication
    handlers {
        fence-peer "/usr/lib/drbd/crm-fence-peer.sh";
        after-resync-target "/usr/lib/drbd/crm-unfence-peer.sh";
    }
}

resource nfs-data {
    on nfs-primary {
        device    /dev/drbd0;
        disk      /dev/sdb1;
        address   192.168.1.10:7789;
        meta-disk internal;
    }
    on nfs-secondary {
        device    /dev/drbd0;
        disk      /dev/sdb1;
        address   192.168.1.11:7789;
        meta-disk internal;
    }
}
```

Protocol C ensures that every write is acknowledged only after both nodes have confirmed it on disk. This provides zero data loss but adds latency proportional to the network round-trip time between nodes.

### NFS Export Configuration

```
/data 192.168.1.0/24(rw,sync,no_root_squash,no_subtree_check)
```

For failover, use Corosync and Pacemaker to manage the floating IP and NFS service:

```bash
# Create the Pacemaker cluster
pcs cluster setup --name nfs-cluster nfs-primary nfs-secondary
pcs cluster start --all

# Configure resources
pcs resource create drbd_nfs ocf:linbit:drbd   drbd_resource=nfs-data op monitor interval=30s

pcs resource master drbd_nfs-clone drbd_nfs   master-max=1 master-node-max=1 clone-max=2 clone-node-max=1

pcs resource create nfs-server systemd:nfs-server   op monitor interval=30s

pcs resource create nfs-ip IPaddr2   ip=192.168.1.100 cidr_netmask=24 op monitor interval=30s

# Colocation constraints
pcs constraint order promote drbd_nfs-clone then start nfs-server
pcs constraint colocation add nfs-server with drbd_nfs-clone INFINITY
pcs constraint colocation add nfs-ip with nfs-server INFINITY
```

## GlusterFS Geo-Replication: Asynchronous File Replication

GlusterFS is a distributed filesystem that natively supports NFS exports through its NFS-Ganesha gateway. Geo-replication provides asynchronous file-level replication between GlusterFS volumes, making it suitable for cross-site disaster recovery.

### Docker Compose Deployment

```yaml
version: "3.8"
services:
  gluster-node1:
    image: gluster/gluster-centos:latest
    container_name: gluster-node1
    hostname: gluster-node1
    privileged: true
    cap_add:
      - SYS_ADMIN
      - NET_ADMIN
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
      - gluster-data1:/var/lib/glusterd
      - gluster-brick1:/data/brick1
    ports:
      - "24007:24007"
      - "49152:49152"
    restart: unless-stopped

  gluster-node2:
    image: gluster/gluster-centos:latest
    container_name: gluster-node2
    hostname: gluster-node2
    privileged: true
    cap_add:
      - SYS_ADMIN
      - NET_ADMIN
    volumes:
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
      - gluster-data2:/var/lib/glusterd
      - gluster-brick2:/data/brick2
    ports:
      - "24008:24007"
      - "49153:49152"
    restart: unless-stopped

volumes:
  gluster-data1:
  gluster-data2:
  gluster-brick1:
  gluster-brick2:
```

### GlusterFS Volume and Geo-Rep Setup

```bash
# Probe the peer
gluster peer probe gluster-node2

# Create a replicated volume
gluster volume create nfs-volume replica 2   gluster-node1:/data/brick1/nfs-volume   gluster-node2:/data/brick2/nfs-volume force

gluster volume start nfs-volume

# Enable NFS access
gluster volume set nfs-volume nfs.disable off
gluster volume set nfs-volume nfs.addr-namelookup off

# Set up geo-replication to a remote site
gluster volume geo-replication nfs-volume   georep-user@remote-site::remote-volume create push-pem force

gluster volume geo-replication nfs-volume   georep-user@remote-site::remote-volume start
```

GlusterFS geo-replication uses a changelog-based mechanism to track file modifications and replicate them asynchronously to the remote site. The replication interval depends on the `georep-checkpoint-time` setting (default: 60 seconds).

### NFS Mount from Clients

```bash
# Mount the GlusterFS volume via NFS
mount -t nfs gluster-node1:/nfs-volume /mnt/shared

# Or mount directly via GlusterFS native protocol (better performance)
mount -t glusterfs gluster-node1:/nfs-volume /mnt/shared
```

## Pacemaker HA NFS: Resource-Level Failover

Pacemaker is a high-availability cluster resource manager that can orchestrate NFS failover across two or more nodes. Unlike DRBD, Pacemaker does not handle data replication — it manages the floating IP, NFS service, and the underlying storage (which could be DRBD, shared iSCSI, or a SAN).

### Cluster Architecture

```
                    ┌──────────────────┐
  Clients ─────────→│ Virtual IP        │
                    │ 192.168.1.100     │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │                              │
     ┌────────▼────────┐          ┌──────────▼────────┐
     │ Node A (Active)  │          │ Node B (Passive)   │
     │ - NFS Server     │          │ - NFS Server       │
     │ - Filesystem     │          │ - Filesystem       │
     │ - Corosync/Pacemaker         │ - Corosync/Pacemaker
     └─────────────────┘          └──────────────────┘
```

### Pacemaker Resource Configuration

```bash
# Enable STONITH (Shoot The Other Node In The Head) fencing
pcs property set stonith-enabled=true
pcs property set no-quorum-policy=freeze

# Create a filesystem resource (shared storage via iSCSI)
pcs resource create nfs-fs Filesystem   device="/dev/mapper/mpatha"   directory="/srv/nfs"   fstype="ext4"   op monitor interval=30s

# Create NFS server resource
pcs resource create nfs-daemon nfsserver   nfs_shared_infodir="/var/lib/nfs"   op monitor interval=30s

# Create NFS export resource
pcs resource create nfs-export exportfs   clientspec="192.168.1.0/24"   options="rw,sync,no_root_squash,no_subtree_check"   directory="/srv/nfs"   fsid=0   op monitor interval=30s

# Create floating IP resource
pcs resource create nfs-vip IPaddr2   ip=192.168.1.100 cidr_netmask=24   op monitor interval=30s

# Define ordering and colocation
pcs constraint order start nfs-fs then nfs-daemon
pcs constraint order start nfs-daemon then nfs-export
pcs constraint order start nfs-export then nfs-vip
pcs constraint colocation add nfs-vip with nfs-export INFINITY
```

The key difference between Pacemaker-only and DRBD+Pacemaker is the storage layer. With DRBD, each node has its own local disk that gets replicated. With Pacemaker on shared storage (iSCSI, SAN, multipath), only one node can access the disk at a time, and fencing ensures that the passive node releases the disk before the active node mounts it.

## Choosing the Right NFS HA Solution

**Use DRBD + NFS when:**
- You need synchronous replication with zero data loss
- You have two servers with direct network connectivity (low latency)
- You want commodity hardware (no shared SAN required)
- Your workload is write-intensive and needs consistent replication

**Use GlusterFS Geo-Replication when:**
- You need cross-site disaster recovery over WAN links
- Asynchronous replication is acceptable (minutes of data loss)
- You want active-active access (both sites can serve reads)
- You're already running GlusterFS for distributed storage

**Use Pacemaker HA NFS when:**
- You have shared storage (SAN, iSCSI, multipath) already available
- You need a proven enterprise HA stack with STONITH fencing
- You want integration with existing cluster infrastructure
- You need to manage additional services alongside NFS (database, web server)

## Why Self-Host NFS High Availability?

Self-hosting your NFS infrastructure with built-in redundancy eliminates vendor lock-in, reduces costs, and gives you complete control over storage performance and data placement.

**Eliminate single points of failure**: A single NFS server failure can disrupt dozens or hundreds of client systems simultaneously — build servers, CI/CD runners, container orchestration platforms, and developer workstations all depend on shared storage. HA configurations ensure automatic failover with minimal disruption.

**Cost efficiency**: Enterprise NFS HA appliances from NetApp or Dell EMC cost tens of thousands of dollars. Open-source alternatives using DRBD, GlusterFS, and Pacemaker provide equivalent functionality on commodity hardware at a fraction of the cost. Two standard servers with DRBD replication can handle terabytes of NFS storage for under $5,000 in hardware.

**Data sovereignty**: Self-hosted NFS keeps your data on infrastructure you control. For organizations handling sensitive data subject to regulatory compliance (GDPR, HIPAA, SOC 2), storing data on-premises with open-source tools eliminates the risk of cloud provider data access or geographic jurisdiction issues.

**Performance tuning**: Self-hosted NFS lets you tune every parameter — NFS protocol version (v3 vs v4.2), read/write sizes, commit behavior, and RAID layout — for your specific workload patterns. Cloud NFS services offer limited tuning options and may throttle performance based on shared infrastructure.

For shared storage alternatives, see our [Samba vs NFS vs WebDAV comparison](../2026-04-24-samba-vs-nfs-vs-webdav-self-hosted-file-sharing-guide-2026/). For distributed filesystems, our [JuiceFS vs Alluxio vs CephFS guide](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/) covers cluster-wide storage solutions.

## FAQ

### What is the difference between DRBD protocol A, B, and C?

Protocol A (asynchronous) acknowledges writes after the primary node writes to its local disk — fastest but risks data loss if the primary fails before replication completes. Protocol B (semi-synchronous) acknowledges after data reaches the primary's memory buffer and is in flight to the secondary. Protocol C (synchronous) acknowledges only after both nodes have written to disk — zero data loss but highest latency.

### Can DRBD work over a WAN connection?

Yes, but you should use protocol A (asynchronous) or DRBD's proxy mode to avoid latency penalties. Protocol C over a WAN with 50ms round-trip time would add 50ms to every write operation, which is unacceptable for most workloads. For cross-site DRBD, consider the async mode with a secondary synchronous pair at each site.

### Does GlusterFS geo-replication support bidirectional sync?

No, GlusterFS geo-replication is unidirectional — changes flow from the master volume to the slave volume only. For bidirectional (active-active) replication, you would need to set up two separate geo-replication sessions in opposite directions, but this risks conflicts if the same file is modified on both sides simultaneously.

### How does Pacemaker handle split-brain scenarios?

Pacemaker uses STONITH (Shoot The Other Node In The Head) fencing to prevent split-brain. When a node is suspected of being down, the cluster uses a fencing agent (IPMI, power switch, or storage-level fencing) to forcibly power off or isolate the suspect node before starting resources on the surviving node. This ensures that only one node can access shared storage at any time.

### Can I use NFSv4 with DRBD failover?

Yes, but NFSv4 maintains stateful connections that must be gracefully handled during failover. Configure `GracePeriod` in your NFS server configuration (typically 90 seconds) to allow clients to reclaim locks after failover. NFSv4.1 and later support session trunking, which can improve failover behavior.

### What happens to NFS clients during a failover?

Clients experience a brief I/O hang (typically 10-30 seconds with hard mount) while the floating IP transfers to the new active node. Once the IP is reachable, NFS clients automatically resume I/O operations. With `soft` mount options, clients may time out and return errors — `hard` mount is recommended for HA configurations. Applications should be designed to handle brief I/O pauses gracefully.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted NFS High Availability: DRBD vs GlusterFS Geo-Replication vs Pacemaker",
  "description": "Compare NFS high availability approaches: DRBD block replication, GlusterFS geo-replication, and Pacemaker cluster management for resilient shared storage.",
  "datePublished": "2026-05-11",
  "dateModified": "2026-05-11",
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
