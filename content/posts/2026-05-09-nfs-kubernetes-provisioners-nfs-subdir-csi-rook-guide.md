---
title: "NFS Kubernetes Provisioners: NFS Subdir vs NFS CSI vs Rook NFS (2026)"
date: "2026-05-09"
tags: ["kubernetes", "nfs", "storage", "csi", "persistent-volumes", "rook", "provisioner"]
draft: false
---

Persistent storage is one of the most challenging aspects of running stateful workloads on Kubernetes. While cloud providers offer managed storage classes with automatic provisioning, self-hosted Kubernetes clusters need their own solution for dynamic PersistentVolume creation. NFS (Network File System) remains the most widely used shared storage protocol for on-premises Kubernetes deployments.

This guide compares three approaches to NFS-based dynamic volume provisioning in Kubernetes: **NFS Subdir External Provisioner** (the simplest), **NFS CSI Driver** (the most feature-rich), and **Rook NFS Operator** (the most comprehensive storage orchestration).

## What Is a Kubernetes Storage Provisioner?

When a user creates a `PersistentVolumeClaim` (PVC) in Kubernetes, the cluster needs a **StorageClass** with a provisioner to dynamically create the underlying `PersistentVolume` (PV). Without a provisioner, you must manually create PVs for every PVC — impractical at scale.

An NFS provisioner automatically:
- Creates a subdirectory on the NFS server when a PVC is requested
- Creates a PV pointing to that subdirectory
- Binds the PV to the PVC
- Cleans up the directory when the PVC is deleted

## NFS Subdir External Provisioner

The NFS Subdir External Provisioner ([github.com/kubernetes-sigs/nfs-subdir-external-provisioner](https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner)) is the simplest and most widely used NFS provisioner. Maintained by the Kubernetes SIGs, it has 3,002 stars and is the go-to solution for basic NFS dynamic provisioning.

### Architecture

This provisioner runs as a Deployment in your cluster. It watches for PVCs that reference its StorageClass, then creates a subdirectory on the NFS server (e.g., `/exports/pvc-namespace-claimname-uuid`) and creates the corresponding PV.

### Installation via Helm

```bash
# Add the Helm repository
helm repo add nfs-subdir-external-provisioner https://kubernetes-sigs.github.io/nfs-subdir-external-provisioner/
helm repo update

# Install with your NFS server details
helm install nfs-provisioner nfs-subdir-external-provisioner/nfs-subdir-external-provisioner \
    --set nfs.server=192.168.1.100 \
    --set nfs.path=/exports \
    --set storageClass.name=nfs-subdir \
    --set storageClass.defaultClass=true
```

### Manual YAML Installation

```yaml
# storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-subdir
provisioner: k8s-sigs.io/nfs-subdir-external-provisioner
parameters:
  archiveOnDelete: "false"  # Set to "true" to preserve data on PVC delete
reclaimPolicy: Delete
volumeBindingMode: Immediate
```

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nfs-subdir-external-provisioner
  namespace: kube-system
spec:
  replicas: 1
  strategy:
    type: Recreate
  template:
    spec:
      serviceAccountName: nfs-client-provisioner
      containers:
        - name: nfs-client-provisioner
          image: registry.k8s.io/sig-storage/nfs-subdir-external-provisioner:v4.0.2
          volumeMounts:
            - name: nfs-client-root
              mountPath: /persistentvolumes
          env:
            - name: PROVISIONER_NAME
              value: k8s-sigs.io/nfs-subdir-external-provisioner
            - name: NFS_SERVER
              value: "192.168.1.100"
            - name: NFS_PATH
              value: "/exports"
      volumes:
        - name: nfs-client-root
          nfs:
            server: 192.168.1.100
            path: /exports
```

### Usage Example

```yaml
# pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: my-app-data
spec:
  storageClassName: nfs-subdir
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 10Gi
```

### When to Use

- Small to medium clusters (up to ~50 nodes)
- Simple "NFS server + subdirectory" storage model
- Quick setup for development/testing environments
- Minimal operational overhead

### Limitations

| Limitation | Impact |
|---|---|
| No resize support | Cannot expand PVCs after creation |
| No snapshot support | No VolumeSnapshot integration |
| Single NFS server | No failover or load balancing |
| Basic permissions | No per-PVC ownership or quota enforcement |
| No topology awareness | Cannot schedule pods based on storage locality |

## NFS CSI Driver

The NFS CSI Driver ([github.com/kubernetes-csi/csi-driver-nfs](https://github.com/kubernetes-csi/csi-driver-nfs)) is the official CSI-based NFS driver from the Kubernetes CSI team. With 1,264 stars, it provides richer functionality than the subdir provisioner.

### Architecture

CSI (Container Storage Interface) is the standard plugin architecture for storage in Kubernetes. The NFS CSI driver implements the full CSI specification, enabling advanced features like volume resizing, snapshots, and topology-aware scheduling.

### Installation via Helm

```bash
helm repo add csi-driver-nfs https://raw.githubusercontent.com/kubernetes-csi/csi-driver-nfs/master/charts
helm repo update

helm install csi-driver-nfs csi-driver-nfs/csi-driver-nfs \
    --namespace kube-system \
    --set feature.volumeCloning=true \
    --set feature.enableInlineVolume=true
```

### StorageClass Configuration

```yaml
# nfs-csi-storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: nfs-csi
provisioner: nfs.csi.k8s.io
parameters:
  server: 192.168.1.100
  share: /exports
  subDir: "$${pvc.namespace}-$${pvc.name}"  # Dynamic subdirectory per PVC
  mountPermissions: "0770"  # Set directory permissions
  mountOptions:
    - nfsvers=4.1
    - nconnect=8  # Enable multi-threaded NFS (Linux 5.3+)
    - hard
    - timeo=600
    - retrans=2
reclaimPolicy: Delete
volumeBindingMode: Immediate
allowVolumeExpansion: true  # CSI advantage: supports resize
```

### Volume Snapshot Support

```yaml
# volumesnapshotclass.yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: nfs-csi-snapclass
driver: nfs.csi.k8s.io
deletionPolicy: Delete
parameters:
  snapshottype: nfs  # Implementation-specific
```

### Usage with Inline Volume (Pod-level, no PVC needed)

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: inline-nfs-pod
spec:
  containers:
    - name: app
      image: nginx:alpine
      volumeMounts:
        - name: nfs-vol
          mountPath: /data
  volumes:
    - name: nfs-vol
      csi:
        driver: nfs.csi.k8s.io
        volumeAttributes:
          server: 192.168.1.100
          share: /exports/my-app
        volumeHandle: unique-volume-id
```

### When to Use

- Production clusters requiring volume resizing
- Need VolumeSnapshot integration for backup workflows
- Multi-cluster setups requiring consistent CSI interfaces
- Environments using advanced mount options (nconnect, specific NFS versions)

### Limitations

| Limitation | Impact |
|---|---|
| CSI driver installation complexity | More components to manage |
| No native NFS server management | Requires separate NFS server |
| Snapshot support varies | Depends on CSI driver version |
| No storage orchestration | Still manual NFS server management |

## Rook NFS Operator

Rook ([github.com/rook/rook](https://github.com/rook/rook)) is a cloud-native storage orchestrator that supports Ceph, NFS, and other backends. With 13,495 stars, it's the most comprehensive storage solution for Kubernetes. The Rook NFS operator manages the entire NFS server lifecycle within Kubernetes.

### Architecture

Unlike the previous two options (which assume an external NFS server), Rook NFS **runs the NFS server inside Kubernetes**. The operator manages NFS server Pods, handles failover, and provides dynamic provisioning through a StorageClass.

### Installation

```bash
# Install Rook operator
helm repo add rook-release https://charts.rook.io/release
helm repo update

helm install rook-ceph rook-release/rook-ceph \
    --namespace rook-ceph \
    --create-namespace

# Deploy NFS CRD and operator
kubectl apply -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/nfs-crd.yaml
kubectl apply -f https://raw.githubusercontent.com/rook/rook/master/deploy/examples/nfs-operator.yaml
```

### NFS Cluster Definition

```yaml
# nfs-cluster.yaml
apiVersion: nfs.rook.io/v1alpha1
kind: NFSServer
metadata:
  name: my-nfs
  namespace: rook-ceph
spec:
  replicas: 2  # High-availability NFS servers
  volumeClaimTemplate:
    spec:
      storageClassName: rook-ceph-block
      resources:
        requests:
          storage: 100Gi
  exports:
    - name: shared-data
      persistentVolumeClaim:
        claimName: nfs-data-pvc
      accessMode: ReadWriteMany
      squash: "none"
      readOnly: false
```

### StorageClass for Rook NFS

```yaml
# rook-nfs-storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: rook-nfs
provisioner: nfs.rook.io/rook-nfs-provisioner
parameters:
  # Rook NFS creates its own exports automatically
  clusterName: my-nfs
  clusterNamespace: rook-ceph
reclaimPolicy: Delete
volumeBindingMode: Immediate
```

### When to Use

- You want the NFS server managed by Kubernetes (no separate infrastructure)
- Need high-availability NFS with automatic failover
- Already running Rook Ceph for block/object storage
- Multi-tenant environments needing isolated NFS exports

### Limitations

| Limitation | Impact |
|---|---|
| High operational complexity | Full Rook stack to manage |
| Requires Ceph for backend storage | Additional infrastructure requirement |
| Resource-intensive | NFS servers consume cluster resources |
| Overkill for simple setups | Heavy machinery for basic NFS needs |

## Comparison: NFS Kubernetes Provisioners

| Feature | NFS Subdir External | NFS CSI Driver | Rook NFS |
|---|---|---|---|
| **GitHub Stars** | 3,002 | 1,264 | 13,495 |
| **Maintained By** | Kubernetes SIGs | Kubernetes CSI Team | Rook Community |
| **NFS Server** | External (pre-existing) | External (pre-existing) | Managed in-cluster |
| **Dynamic Provisioning** | Yes (subdirectory) | Yes (subdirectory) | Yes (exports) |
| **Volume Resize** | No | Yes | Yes |
| **Volume Snapshots** | No | Yes (CSI) | Via Ceph backend |
| **High Availability** | No (single provisioner) | No (single driver) | Yes (replicated NFS) |
| **Mount Options** | Basic | Advanced (nconnect, vers) | Advanced |
| **Inline Volumes** | No | Yes | No |
| **Topology Awareness** | No | Yes | Yes |
| **Installation** | Helm (simple) | Helm (moderate) | Helm + CRDs (complex) |
| **Resource Usage** | Minimal | Low | High (in-cluster NFS) |
| **Best For** | Dev/test, simple clusters | Production, resize needed | Full storage orchestration |

## Why Self-Host NFS Storage for Kubernetes?

Running your own NFS provisioner instead of relying on cloud-managed storage classes gives you complete control over your data lifecycle and cost structure.

For related storage comparisons, see our [distributed filesystem guide](../2026-04-28-juicefs-vs-alluxio-vs-cephfs-self-hosted-distribu/) and [NFS server setup article](../2026-04-30-nfs-ganesha-vs-unfs3-vs-kernel-nfs-self-hosted-nfs-server-guide-2026/). If you are managing Kubernetes clusters, our [CNI plugin comparison](../2026-04-21-flannel-vs-calico-vs-cilium-self-hosted-kubernetes-cni-guide-2026/) covers the networking layer that complements your storage setup.

**Data Ownership and Portability**: When you manage your own NFS server, your data lives on infrastructure you control. There's no vendor-specific storage API locking you into a particular cloud provider. The same PVC definitions work identically on bare metal, colocation, or any cloud — your storage follows the NFS protocol, which is universally supported.

**Cost Savings at Scale**: Cloud-managed Kubernetes storage classes charge premium rates for persistent volumes — often 2-3x the cost of raw storage. By running your own NFS server with dynamic provisioning, you pay only for the underlying disk hardware. For clusters with hundreds of PVCs, this difference adds up to thousands of dollars per month.

**Performance Tuning**: Self-hosted NFS lets you tune mount options (NFS version, readahead, nconnect threads), use local SSDs for caching, and deploy dedicated 10Gbps+ network links between the NFS server and Kubernetes nodes. Cloud storage classes offer limited tuning knobs and often share underlying storage infrastructure with other tenants.

**Backup and Disaster Recovery**: With your own NFS server, you choose the backup strategy — rsync to offsite storage, ZFS snapshots, or integration with enterprise backup tools. Cloud storage snapshots are convenient but expensive and vendor-specific.

## FAQ

### Which NFS provisioner should I choose for my cluster?

For development and testing, use the **NFS Subdir External Provisioner** — it's the simplest to set up and has the lowest overhead. For production clusters that need volume resizing and snapshots, use the **NFS CSI Driver**. If you need in-cluster NFS server management with high availability, use **Rook NFS**.

### Can I use NFS provisioners with ReadWriteOnce volumes?

Yes, all three provisioners support both `ReadWriteMany` (RWX) and `ReadWriteOnce` (RWO) access modes. RWX is the primary advantage of NFS — multiple pods on different nodes can read and write to the same volume simultaneously.

### What NFS version should I use?

NFSv4.1 is recommended for Kubernetes workloads. It supports parallel NFS (pNFS), improved locking, and better performance than NFSv3. For Linux 5.3+ kernels, enable `nconnect=8` mount option for multi-threaded NFS connections that significantly improve throughput.

### How do I back up NFS-provisioned volumes?

Use **Velero** with CSI snapshot support (NFS CSI driver), or run periodic `rsync` from the NFS server to backup storage. For Rook NFS with Ceph backend, use Ceph's native snapshot and replication features. See our [Velero backup orchestration guide](../velero-vs-stash-vs-volsync-kubernetes-backup-orchestration-guide-2026/) for detailed backup strategies.

### Can I migrate from NFS Subdir to NFS CSI without data loss?

Yes. The NFS CSI driver can use the same NFS server and export path. Create a new StorageClass with the CSI driver, point it to the same NFS server, and use the same base path. New PVCs will be provisioned by CSI, and existing PVCs continue to work. You can gradually migrate by recreating workloads with the new StorageClass.

### Does NFS storage work for databases?

NFS is generally not recommended for databases that require high IOPS and low latency (PostgreSQL, MySQL, Elasticsearch). Use block storage (Rook Ceph, Longhorn) for databases. NFS is ideal for web servers, CI/CD caches, shared configuration, log aggregation, and media processing workloads where concurrent read/write access matters more than raw IOPS.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "NFS Kubernetes Provisioners: NFS Subdir vs NFS CSI vs Rook NFS (2026)",
  "description": "Compare NFS Subdir External Provisioner, NFS CSI Driver, and Rook NFS for dynamic Kubernetes storage provisioning. Setup, Helm configs, and production deployment patterns.",
  "datePublished": "2026-05-09",
  "dateModified": "2026-05-09",
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
