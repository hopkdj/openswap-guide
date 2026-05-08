---
title: "Kubernetes CSI Drivers: Ceph CSI vs Longhorn vs Kadalu (2026)"
date: "2026-05-08"
tags: ["kubernetes", "storage", "csi", "ceph", "longhorn", "kadalu", "persistent-volumes", "cloud-native"]
draft: false
---

The Container Storage Interface (CSI) is the standard that Kubernetes uses to manage persistent storage for stateful workloads. Rather than baking storage drivers directly into the kubelet code, CSI enables third-party storage providers to deploy their own plugins as separate containers — giving you the flexibility to mix and match storage backends on a per-namespace or per-volume basis.

In this guide, we compare three popular open-source CSI drivers: **Ceph CSI**, **Longhorn**, and **Kadalu**. Each takes a different approach to persistent storage in Kubernetes, and understanding their trade-offs is critical for building reliable stateful clusters.

## What Is a CSI Driver?

CSI is a specification that defines how storage systems integrate with container orchestration platforms like Kubernetes. Before CSI, each storage plugin had to be compiled into the Kubernetes source tree — a tightly coupled model that slowed innovation and created compatibility headaches.

With CSI, storage vendors ship independent plugins that communicate with the kubelet through a well-defined gRPC API. This means:

- **Storage providers** can release updates independently of Kubernetes releases
- **Cluster administrators** can install, upgrade, or remove storage plugins without touching the control plane
- **Developers** get a consistent experience regardless of the underlying storage backend

A CSI driver typically consists of three sidecar containers: an external provisioner (creates/deletes volumes), an external attacher (attaches volumes to nodes), and an external resizer (resizes volumes). The driver itself exposes the Controller and Node gRPC services.

## Comparison Table

| Feature | Ceph CSI | Longhorn CSI | Kadalu CSI |
|---------|----------|--------------|------------|
| **Backend** | Ceph RBD / CephFS | Distributed block storage | GlusterFS |
| **Stars** | 1,532+ | 7,693+ | 749+ |
| **Block Storage** | Yes (RBD) | Yes | Yes (via Gluster) |
| **File Storage** | Yes (CephFS) | No | Yes |
| **Snapshot Support** | Yes (CSI VolumeSnapshot) | Yes | Yes |
| **Volume Expansion** | Yes (online) | Yes (online) | Yes |
| **Encryption** | Yes (LUKS) | Yes (disk-level) | No |
| **Replication** | Built into Ceph CRUSH | Synchronous replica chain | Gluster replica |
| **Minimum Nodes** | 3 (Ceph cluster) | 3 | 3 |
| **Helm Chart** | Yes | Yes | Yes |
| **ARM Support** | Yes | Yes | Yes |
| **NVMe Support** | Yes | Limited | No |
| **Project URL** | [github.com/ceph/ceph-csi](https://github.com/ceph/ceph-csi) | [github.com/longhorn/longhorn](https://github.com/longhorn/longhorn) | [github.com/kadalu/kadalu](https://github.com/kadalu/kadalu) |

## Ceph CSI Driver

Ceph CSI is the official Container Storage Interface driver for Ceph, the massively scalable distributed storage platform. It exposes both Ceph RBD (block device) and CephFS (distributed file system) to Kubernetes workloads through a single plugin.

### Architecture

Ceph CSI operates as a set of Kubernetes DaemonSets and Deployments. The controller plugin runs as a Deployment (one replica) and handles volume provisioning, deletion, and snapshotting. The node plugin runs as a DaemonSet on every Kubernetes node and handles volume mounting, unmounting, and staging.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: ceph-rbd
provisioner: rbd.csi.ceph.com
parameters:
  clusterID: ceph-cluster-id
  pool: kubernetes-rbd
  imageFeatures: layering
  csi.storage.k8s.io/provisioner-secret-name: csi-rbd-secret
  csi.storage.k8s.io/provisioner-secret-namespace: rook-ceph
  csi.storage.k8s.io/controller-expand-secret-name: csi-rbd-secret
  csi.storage.k8s.io/controller-expand-secret-namespace: rook-ceph
  csi.storage.k8s.io/node-stage-secret-name: csi-rbd-secret
  csi.storage.k8s.io/node-stage-secret-namespace: rook-ceph
  csi.storage.k8s.io/fstype: ext4
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: Immediate
```

### Docker Compose (Ceph Cluster)

```yaml
version: "3.8"
services:
  mon:
    image: quay.io/ceph/daemon:latest
    command: ["ceph-mon"]
    environment:
      - CEPH_MON_NETWORK=10.0.0.0/24
      - CLUSTER=ceph
    volumes:
      - /etc/ceph:/etc/ceph
      - /var/lib/ceph:/var/lib/ceph
      - /dev:/dev
    network_mode: host
    privileged: true
  mgr:
    image: quay.io/ceph/daemon:latest
    command: ["ceph-mgr"]
    environment:
      - CLUSTER=ceph
    volumes:
      - /etc/ceph:/etc/ceph
      - /var/lib/ceph:/var/lib/ceph
    network_mode: host
    privileged: true
  osd:
    image: quay.io/ceph/daemon:latest
    command: ["ceph-osd"]
    environment:
      - CLUSTER=ceph
      - OSD_DEVICE=/dev/vdb
    volumes:
      - /etc/ceph:/etc/ceph
      - /var/lib/ceph:/var/lib/ceph
      - /dev:/dev
    network_mode: host
    privileged: true
```

### When to Choose Ceph CSI

Ceph CSI is the right choice when you already run a Ceph cluster or need the highest level of storage durability and scalability. Ceph's CRUSH algorithm provides automatic data distribution across OSDs, and the RBD protocol delivers near-native performance. It's the most feature-complete CSI driver but also the most complex to operate.

## Longhorn CSI Driver

Longhorn is a cloud-native distributed block storage system built specifically for Kubernetes. Unlike Ceph CSI which connects to an external Ceph cluster, Longhorn runs entirely within your Kubernetes cluster as a set of pods. Each volume is replicated across multiple nodes using a synchronous replica chain.

### Architecture

Longhorn creates a storage network within your cluster. Every volume is split into replicas, and each replica runs as a pod on a different node. Writes go through a frontend (block device or iSCSI) to the primary replica, which synchronously replicates to secondary replicas. This provides strong consistency guarantees.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn
provisioner: driver.longhorn.io
allowVolumeExpansion: true
parameters:
  numberOfReplicas: "3"
  staleReplicaTimeout: "30"
  fromBackup: "
  fsType: ext4
  dataLocality: "best-effort"
reclaimPolicy: Delete
volumeBindingMode: Immediate
```

### Docker Compose (Standalone Longhorn Manager)

While Longhorn is designed to run inside Kubernetes, you can deploy a minimal management stack:

```yaml
version: "3.8"
services:
  longhorn-manager:
    image: longhornio/longhorn-manager:v1.7.0
    command: ["longhorn-manager", "-d", "daemon", "--engine-image", "longhornio/longhorn-engine:v1.7.0"]
    environment:
      - NODE_NAME=node1
    volumes:
      - /dev:/host/dev
      - /proc:/host/proc
      - /var/lib/longhorn:/var/lib/longhorn
      - /var/run:/host/var/run
    privileged: true
    network_mode: host
  longhorn-ui:
    image: longhornio/longhorn-ui:v1.7.0
    ports:
      - "8000:8000"
    environment:
      - LONGHORN_MANAGER_IP=http://localhost:9500
```

### When to Choose Longhorn

Longhorn excels when you want Kubernetes-native storage without managing a separate cluster. Its built-in UI provides visibility into volume health, replica placement, and backup status. It's ideal for edge deployments, development clusters, and teams that want operational simplicity without sacrificing data durability.

## Kadalu CSI Driver

Kadalu provides a lightweight CSI driver backed by GlusterFS. It's designed to be simple to deploy and operate, with a focus on small-to-medium Kubernetes clusters that need persistent storage without the operational overhead of Ceph.

### Architecture

Kadalu uses GlusterFS as the storage backend but abstracts away the complexity of Gluster configuration. You define storage pools from available disks, and Kadalu automatically creates Gluster volumes and exposes them through the CSI interface.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: kadalu.replicated
provisioner: kadalu
parameters:
  type: "Replica3"
  volume-id: "storage-pool-1"
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: Immediate
```

### Docker Compose (Gluster Backend)

```yaml
version: "3.8"
services:
  glusterfs:
    image: gluster/gluster-centos:latest
    command: ["/usr/sbin/glusterd", "-f", "--no-daemon"]
    volumes:
      - /dev:/dev
      - /data/gluster:/data/gluster
      - /var/lib/glusterd:/var/lib/glusterd
      - /sys/fs/cgroup:/sys/fs/cgroup:ro
    privileged: true
    network_mode: host
    cap_add:
      - SYS_ADMIN
      - DAC_READ_SEARCH
```

### When to Choose Kadalu

Kadalu is a strong option when you want GlusterFS-like storage with Kubernetes-native management. It's lighter weight than Ceph and simpler to configure than raw GlusterFS. The trade-off is a smaller feature set and less mature ecosystem compared to Ceph CSI and Longhorn.

## Choosing the Right CSI Driver

| Criteria | Ceph CSI | Longhorn | Kadalu |
|----------|----------|----------|--------|
| **Large-scale production** | Best | Good | Fair |
| **Edge / small cluster** | Overkill | Excellent | Good |
| **File sharing (RWX)** | Excellent (CephFS) | No | Good |
| **Block performance** | Excellent | Good | Fair |
| **Operational complexity** | High | Low | Medium |
| **Community size** | Large | Large | Small |
| **Enterprise support** | Red Hat / SUSE | SUSE | Community |

For **production clusters with demanding I/O workloads**, Ceph CSI delivers the best performance and scalability. Its RBD protocol supports features like deep flattening, image mirroring, and encryption at rest.

For **simplicity and Kubernetes-native operation**, Longhorn is unmatched. It runs entirely as pods inside your cluster, includes a built-in UI, and handles replication automatically.

For **lightweight GlusterFS-based storage**, Kadalu provides a straightforward path to persistent volumes without the complexity of managing a full Ceph deployment.

## Why Self-Host Your CSI Driver?

Running your own CSI drivers gives you complete control over data placement, replication policies, and encryption settings. When you manage storage within your Kubernetes cluster, you eliminate dependency on external storage providers and avoid vendor lock-in.

Self-hosted CSI drivers also integrate seamlessly with your existing infrastructure. If you already run a Ceph cluster for OpenStack or virtual machines, Ceph CSI lets Kubernetes tap into that same storage pool. If you need per-volume backup and snapshot capabilities, Longhorn provides built-in backup to S3-compatible stores.

For organizations with compliance requirements, self-hosted storage means your data never leaves your infrastructure. There are no egress charges, no external API calls, and no third-party access to your persistent volumes.

For disaster recovery planning, see our [Ceph deployment guide](../2026-05-15-self-hosted-ceph-deployment-cephadm-vs-rook-vs-ceph-ansible-guide/). For a broader look at Kubernetes storage options, our [Rook vs Longhorn vs OpenEBS comparison](../rook-vs-longhorn-vs-openebs-self-hosted-kubernetes-storage-guide-2026/) covers the storage systems behind these CSI drivers. If you're also evaluating distributed file systems, check our [JuiceFS vs Alluxio vs CephFS guide](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distributed-file-systems-2026/).

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kubernetes CSI Drivers: Ceph CSI vs Longhorn vs Kadalu (2026)",
  "description": "Compare three open-source Kubernetes CSI drivers for persistent storage. Learn when to choose Ceph CSI, Longhorn CSI, or Kadalu CSI for your stateful workloads.",
  "datePublished": "2026-05-08",
  "dateModified": "2026-05-08",
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

## FAQ

### What is a CSI driver in Kubernetes?

A CSI (Container Storage Interface) driver is a plugin that enables Kubernetes to communicate with external storage systems. It implements a standard gRPC API for volume provisioning, attachment, mounting, and snapshotting. CSI drivers run as separate containers alongside the kubelet, allowing storage providers to update their plugins independently of Kubernetes releases.

### Can I use multiple CSI drivers in the same cluster?

Yes. Kubernetes supports any number of CSI drivers simultaneously. You create separate StorageClass objects for each driver and select the appropriate one in your PersistentVolumeClaim spec. For example, you might use Ceph CSI for high-performance databases and Longhorn for general-purpose application data.

### Does Ceph CSI support volume encryption?

Yes. Ceph CSI supports encryption at rest through Linux LUKS (Linux Unified Key Setup). When you enable encryption in the StorageClass parameters, the CSI driver creates an encrypted RBD image and maps it through cryptsetup on the node. The encryption key is managed by Kubernetes secrets or an external key management system like HashiCorp Vault.

### How does Longhorn handle node failures?

Longhorn uses synchronous replication across multiple nodes. When a volume has 3 replicas and one node goes offline, the remaining two replicas continue serving I/O. When the failed node returns, Longhorn automatically rebuilds the missing replica by copying data from an existing replica. This process is transparent to the workload.

### What is the minimum cluster size for Kadalu?

Kadalu requires a minimum of 3 nodes for Replica3 configuration (the default). For smaller clusters, you can use Replica2 or Disperse (erasure coding) storage types. Kadalu also supports External storage type where you connect to an existing GlusterFS cluster outside of Kubernetes.

### Can CSI drivers perform online volume expansion?

Yes. All three drivers — Ceph CSI, Longhorn, and Kadalu — support online volume expansion through the CSI ControllerExpandVolume RPC. When you increase the size of a PersistentVolumeClaim, the CSI driver expands the underlying volume and the filesystem without requiring pod restarts. Ceph CSI additionally supports online resizing of encrypted volumes.
