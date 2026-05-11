---
title: "Self-Hosted Kubernetes CSI Snapshot Management: External-Snapshotter vs Stash vs Velero"
date: "2026-05-11"
tags: ["kubernetes", "storage", "snapshots", "csi", "backup"]
draft: false
---

Kubernetes persistent volumes hold critical application data, and protecting that data requires reliable snapshot capabilities with proper lifecycle management and automated retention policies. The Container Storage Interface (CSI) introduced a standardized way to create volume snapshots, but managing those snapshots at scale demands dedicated tooling. This guide compares three approaches to Kubernetes CSI snapshot management: the official CSI external-snapshotter, AppsCode Stash, and VMware Tanzu Velero.

## What Is CSI Snapshot Management?

The CSI external-snapshotter is a set of sidecar controllers that extend the Kubernetes API with Snapshot and SnapshotContent custom resource definitions (CRDs). It enables storage vendors to expose snapshot capabilities through their CSI drivers. However, the external-snapshotter alone only creates snapshots — it does not manage their lifecycle, retention, scheduling, or restoration. That's where higher-level tools like Stash and Velero come in.

| Feature | CSI External-Snapshotter | AppsCode Stash | Velero |
|---------|-------------------------|----------------|--------|
| **Primary Role** | CSI sidecar controller | Kubernetes backup operator | Cluster backup and migration |
| **GitHub Stars** | 629+ | 1,408+ | 10,008+ |
| **Snapshot Scheduling** | No (requires CronJob) | Built-in BackupSchedule CR | Built-in Schedule CR |
| **Retention Policy** | Manual deletion | TTL-based automatic cleanup | TTL-based automatic cleanup |
| **Cross-Cluster Restore** | No | Limited | Yes (with plugins) |
| **Object Storage Backup** | No (CSI only) | Yes (RESTIC/Kopia) | Yes (RESTIC/Kopia) |
| **Resource Backup** | Snapshots only | K8s resources + volumes | Full cluster resources + volumes |
| **Storage Backend** | CSI driver dependent | Any (S3, GCS, Azure, local) | Any (S3, GCS, Azure, local) |
| **Restore Granularity** | Volume-level | Namespace or volume-level | Namespace, resource, or volume-level |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |

## CSI External-Snapshotter: The Foundation

The external-snapshotter project is maintained by the Kubernetes SIG Storage team and provides the foundational building blocks for CSI snapshot functionality. It consists of four components: the snapshot controller, the CSI snapshotter sidecar, and two CRDs (VolumeSnapshot and VolumeSnapshotContent).

### Installation via Helm

```yaml
# values.yaml for snapshot-controller
replicaCount: 2
image:
  repository: registry.k8s.io/sig-storage/snapshot-controller
  tag: v8.2.0
webhook:
  enabled: true
  port: 8443
```

```bash
# Deploy the snapshot controller
helm install snapshot-controller   --namespace kube-system   oci://registry.k8s.io/sig-storage/snapshot-controller-helm   -f values.yaml

# Verify the CRDs are installed
kubectl get crd | grep snapshot
# volumesnapshotclasses.snapshot.storage.k8s.io
# volumesnapshotcontents.snapshot.storage.k8s.io
# volumesnapshots.snapshot.storage.k8s.io
```

### Creating a Snapshot

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot
  namespace: production
spec:
  volumeSnapshotClassName: csi-hostpath-snapclass
  source:
    persistentVolumeClaimName: postgres-pvc
```

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: csi-hostpath-snapclass
driver: hostpath.csi.k8s.io
deletionPolicy: Delete
parameters:
  csi.storage.k8s.io/snapshot-owner: "true"
```

The external-snapshotter works with any CSI driver that supports the `CREATE_DELETE_SNAPSHOT` controller capability, including AWS EBS CSI, GCE PD CSI, Azure Disk CSI, Longhorn, Rook-Ceph, and many others.

## AppsCode Stash: Cloud-Native Backup for Kubernetes

Stash is a Kubernetes-native backup solution from AppsCode that extends beyond snapshots to provide comprehensive data protection. It uses a BackupConfiguration CRD to define what to back up, when, and where to store it.

### Docker Compose for Self-Hosted Storage Backend

Before deploying Stash, you need an object storage backend. Here's a MinIO deployment for storing backups:

```yaml
version: "3.8"
services:
  minio:
    image: minio/minio:latest
    container_name: stash-minio
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minio-secret-key
    volumes:
      - minio-data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    command: server /data --console-address ":9001"

  create-bucket:
    image: minio/mc:latest
    depends_on:
      - minio
    entrypoint: >
      /bin/sh -c "
      mc alias set local http://minio:9000 minioadmin minio-secret-key;
      mc mb local/stash-backups;
      mc ilm add local/stash-backups --expiry-days 90;
      exit 0;
      "

volumes:
  minio-data:
    driver: local
```

### Stash BackupConfiguration

```yaml
apiVersion: stash.appscode.com/v1beta1
kind: BackupConfiguration
metadata:
  name: postgres-backup
  namespace: production
spec:
  schedule: "0 2 * * *"
  task:
    name: postgres-backup-17
  repository:
    name: minio-repo
  target:
    ref:
      apiVersion: appcatalog.appscode.com/v1alpha1
      kind: AppBinding
      name: postgres-app
  retentionPolicy:
    name: "keep-last-30-daily"
    keepLast: 30
    prune: true
```

Stash integrates directly with CSI snapshots when the driver supports them, falling back to volume-level backups using Kopia or Restic for drivers without snapshot capabilities.

## Velero: Enterprise-Grade Backup and Migration

Velero is the most widely adopted Kubernetes backup solution, originally developed by Heptio and now maintained by VMware Tanzu. It provides comprehensive backup, restore, and migration capabilities.

### Installation

```bash
# Install Velero CLI
curl -L https://github.com/vmware-tanzu/velero/releases/download/v1.15.0/velero-v1.15.0-linux-amd64.tar.gz   -o velero.tar.gz
tar -xzf velero.tar.gz
sudo mv velero-v1.15.0-linux-amd64/velero /usr/local/bin/

# Install Velero server with MinIO backend
velero install   --provider aws   --bucket velero-backups   --secret-file ./credentials-velero   --plugins velero/velero-plugin-for-aws:v1.10.0   --use-volume-snapshots=true   --backup-location-config     region=minio,s3ForcePathStyle=true,s3Url=http://minio:9000
```

### Scheduled Backup with CSI Snapshots

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-postgres
  namespace: velero
spec:
  schedule: "0 2 * * *"
  template:
    includedNamespaces:
      - production
    includedResources:
      - deployments
      - statefulsets
      - persistentvolumeclaims
    snapshotVolumes: true
    storageLocation: default
    volumeSnapshotLocations:
      - default
    ttl: 720h0m0s
```

Velero's CSI integration automatically discovers and uses available CSI snapshot capabilities, falling back to its built-in file-system backup when snapshots are unavailable.

## Choosing the Right CSI Snapshot Tool

**Use CSI External-Snapshotter when:**
- You only need basic snapshot creation and deletion through Kubernetes APIs
- Your CSI driver supports the snapshot controller natively
- You want minimal overhead and no additional operators

**Use AppsCode Stash when:**
- You need application-aware backups (PostgreSQL, MySQL, MongoDB, Redis)
- You want fine-grained backup scheduling and retention policies
- You prefer a Kubernetes-native CRD-based workflow

**Use Velero when:**
- You need cross-cluster backup and disaster recovery
- You want comprehensive cluster resource backup alongside volume snapshots
- You require migration capabilities between clusters or cloud providers

## Why Self-Host Kubernetes Snapshot Management?

Managing volume snapshots in-house gives you complete control over data retention policies, backup scheduling, and storage costs. When you rely on cloud provider snapshots, you're locked into their pricing models and retention limits. Self-hosted snapshot management lets you:

**Control data residency**: Snapshots stay on infrastructure you own and control. For regulated industries with data sovereignty requirements, this is non-negotiable. Your snapshots never leave your data center or chosen cloud region.

**Reduce costs**: Cloud provider snapshots accumulate charges based on provisioned capacity, not actual usage. By routing snapshots to self-hosted object storage (MinIO, Ceph, or commodity S3-compatible storage), you pay only for the bytes you store. A typical production cluster with 50 volumes taking daily snapshots can save 40-60% on storage costs.

**Enable disaster recovery**: Having snapshots stored independently from your primary storage creates a recovery path when the storage cluster itself fails. Velero's cross-cluster restore and Stash's off-cluster repository support make this practical.

**Automate lifecycle management**: Built-in retention policies automatically prune old snapshots based on age, count, or custom labels. Without automation, snapshot sprawl becomes a common problem — administrators create snapshots for testing or debugging and forget to delete them, consuming storage until the cluster runs out of capacity.

For Kubernetes storage fundamentals, see our [NFS Kubernetes provisioners guide](../2026-05-09-nfs-kubernetes-provisioners-nfs-subdir-csi-rook-guide/). If you're evaluating CSI drivers, our [Ceph CSI comparison](../2026-05-08-kubernetes-csi-drivers-ceph-csi-vs-longhorn-vs-kadalu-guide/) covers the leading options. For broader cluster management, the [Rancher vs Kubespray comparison](../2026-04-22-rancher-vs-kubespray-vs-kind-self-hosted-kubernetes-management-guide-2026/) provides deployment guidance.

## FAQ

### What is the difference between CSI snapshots and Velero backups?

CSI snapshots create point-in-time copies of volumes using the storage driver's native snapshot capability. They are fast and storage-efficient but tied to the specific CSI driver. Velero backups include both volume snapshots (when available) and Kubernetes resource manifests (deployments, services, configmaps), enabling full cluster restoration.

### Can I use Velero with any CSI driver?

Velero supports any CSI driver that implements the `CREATE_DELETE_SNAPSHOT` capability. This includes AWS EBS CSI, GCE PD CSI, Azure Disk CSI, Longhorn, Rook-Ceph, OpenEBS, and many others. If your driver does not support CSI snapshots, Velero falls back to file-system-level backup using Kopia or Restic.

### How do I restore a CSI snapshot to a new PersistentVolumeClaim?

Create a new PVC with the `dataSource` field pointing to the VolumeSnapshot:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: restored-postgres-pvc
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: csi-hostpath-sc
  resources:
    requests:
      storage: 10Gi
  dataSource:
    name: postgres-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
```

### Does Stash support incremental backups?

Yes, Stash uses Kopia (recommended) or Restic as the backend, both of which support incremental backups. Only changed blocks are uploaded after the initial full backup, significantly reducing storage usage and backup windows for large datasets.

### How often should I snapshot production volumes?

For databases, hourly snapshots with 24-hour retention is common. For application data, daily snapshots with 30-day retention balances recovery point objectives with storage costs. Critical systems may combine frequent CSI snapshots (every 15 minutes) with less frequent full backups (daily) for defense in depth.

### Can I replicate CSI snapshots to a different cluster?

The external-snapshotter itself does not support cross-cluster replication. However, Velero can export backups to object storage and restore them to any cluster where Velero is installed. Stash similarly supports off-cluster repositories that can be accessed from multiple clusters.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Kubernetes CSI Snapshot Management: External-Snapshotter vs Stash vs Velero",
  "description": "Compare Kubernetes CSI snapshot management tools: the official external-snapshotter, AppsCode Stash, and VMware Tanzu Velero for production data protection.",
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
