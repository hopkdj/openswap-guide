---
title: "Velero vs Stash vs VolSync: Kubernetes Backup Orchestration Guide 2026"
date: 2026-04-19
tags: ["comparison", "guide", "self-hosted", "kubernetes", "backup", "cloud-native"]
draft: false
description: "Compare Velero, Stash, and VolSync for self-hosted Kubernetes backup orchestration. Features, Helm install guides, CRD comparisons, and disaster recovery strategies."
---

Running workloads on [kubernetes](https://kubernetes.io/) without a reliable backup strategy is like building a house on sand. Pods get evicted, nodes fail, storage classes change, and entire clusters can disappear. While Kubernetes handles scheduling and scaling well, **backup and disaster recovery is entirely your responsibility**.

Three open-source projects have emerged as the leading self-hosted solutions for Kubernetes backup orchestration: [Velero](https://velero.io/), [Stash](https://stash.run/), and [VolSync](https://volsync.readthedocs.io/). Each takes a different architectural approach to protecting your cluster state, persistent volumes, and application data.

This guide compares all three tools across features, installation, backup strategies, and operational com[plex](https://www.plex.tv/)ity to help you choose the right solution for your infrastructure.

## Why Back Up Kubernetes at All?

Kubernetes controllers constantly reconcile desired state, but they cannot recreate your data. Persistent Volume Claims (PVCs) hold stateful application data — databases, file uploads, message queues, and configuration stores. When a StorageClass provisioner fails, a disk corrupts, or someone accidentally runs `kubectl delete ns production`, that data is gone without backups.

Even if your cloud provider offers snapshots, those are tied to the provider's storage backend. A self-hosted backup strategy gives you **portability** (restore to any cluster, any provider), **versioning** (roll back to a point in time), and **off-cluster storage** (protect against total cluster loss).

## The Three Contenders at a Glance

| Feature | Velero | Stash | VolSync |
|---|---|---|---|
| **GitHub Stars** | 9,968 | 1,407 | 960 |
| **Last Updated** | Apr 2026 | Apr 2026 | Apr 2026 |
| **Language** | Go | Go | Go |
| **License** | Apache 2.0 | Enterprise/Community | Apache 2.0 |
| **Primary Scope** | Full cluster backup & migration | App-level backup (Kubernetes native) | Volume replication & sync |
| **Backup Targets** | S3, Azure Blob, GCS, generic object storage | S3, GCS, Azure, B2, Restic repos, SFTP | S3, PVC-to-PVC, rsync, rclone, Multicluster |
| **Backup Engine** | Native snapshot API + Restic/Kopia | Restic or Kopia (pluggable) | Restic, rclone, rsync, external-snapshotter |
| **Namespace-Level** | Yes | Yes | Yes |
| **Full Cluster** | Yes | Partial (resource-focused) | No (volume-focused) |
| **Cluster Migration** | Yes (backup + restore to different cluster) | Limited | Limited |
| **Schedule Support** | Built-in Cron-like schedules | Built-in CronJob-based schedules | Built-in ReplicationDestination/Source |
| **Resource Filtering** | Label selectors, namespace include/exclude | Label selectors, namespace targeting | Label selectors, PVC targeting |
| **Hook Support** | Pre/post backup and restore hooks | Pre/post backup and restore hooks | No native hooks |
| **CSI Snapshot** | Yes (CSI VolumeSnapshot integration) | No (uses Restic/Kopia sidecar) | Yes (via external-snapshotter) |
| **Incremental Backup** | Yes (via Restic/Kopia or CSI) | Yes (via Restic/Kopia) | Yes (all backends) |
| **Disaster Recovery** | Full cluster state + data restore | Application data restore | Volume-level restore only |
| **Multi-Cluster** | Via shared object storage | Via shared backend storage | Native multi-cluster sync |
| **Helm Install** | `helm install velero vmware-tanzu/velero` | `helm install stash appscode/stash` | `helm install volsync backube/volsync` |
| **CLI Tool** | `velero` | `kubectl` (CRD-based) | `kubectl` (CRD-based) |
| **Maturity** | Production-ready (since 2017) | Production-ready | Growing adoption (part of ODF) |

## Velero: The Established Standard

[Velero](https://github.com/vmware-tanzu/velero) is the most widely adopted Kubernetes backup solution. Originally developed by Heptio (later acquired by VMware), it has been the de facto standard for cluster backup since 2017.

### How Velero Works

Velero operates as a Kubernetes controller that creates Backup and Restore custom resources. For PersistentVolumes, it supports two modes:

1. **CSI snapshots** — leverages the CSI VolumeSnapshot API for fast, storage-level snapshots (if your CSI driver supports it)
2. **Filesystem backup** — uses Restic or Kopia to back up PV data file-by-file via a DaemonSet sidecar

For Kubernetes resources (Deployments, Services, ConfigMaps, etc.), Velero serializes them to JSON and stores them alongside the PV backup in your object storage.

### Installing Velero via Helm

```bash
# Add the Helm repository
helm repo add vmware-tanzu https://vmware-tanzu.github.io/helm-charts
helm repo update

#[minio](https://min.io/)all Velero with S3-compatible backend (e.g., MinIO)
helm install velero vmware-tanzu/velero \
  --namespace velero \
  --create-namespace \
  --set configuration.backupStorageLocation[0].name=default \
  --set configuration.backupStorageLocation[0].provider=aws \
  --set configuration.backupStorageLocation[0].bucket=k8s-backups \
  --set configuration.backupStorageLocation[0].config.region=minio \
  --set configuration.backupStorageLocation[0].config.s3Url=http://minio:9000 \
  --set configuration.backupStorageLocation[0].config.s3ForcePathStyle=true \
  --set credentials.secretContents.cloud="AWS_ACCESS_KEY_ID=minioadmin\nAWS_SECRET_ACCESS_KEY=minioadmin" \
  --set initContainers[0].name=velero-plugin-for-aws \
  --set initContainers[0].image=velero/velero-plugin-for-aws:v1.10.0 \
  --set initContainers[0].volumeMounts[0].mountPath=/target \
  --set initContainers[0].volumeMounts[0].name=plugins
```

### Creating a Backup

```bash
# Backup an entire namespace
velero backup create myapp-backup --include-namespaces myapp

# Backup with label selector
velero backup create labeled-backup --selector app=myapp

# Schedule daily backups (retained for 30 days)
velero schedule create daily-backup \
  --schedule="0 2 * * *" \
  --ttl 720h \
  --include-namespaces production

# List backups
velero backup get

# Restore from backup
velero restore create --from-backup myapp-backup
```

### Velero Backup CRD Example

```yaml
apiVersion: velero.io/v1
kind: Backup
metadata:
  name: daily-production
  namespace: velero
spec:
  includedNamespaces:
    - production
  storageLocation: default
  ttl: 720h
  snapshotVolumes: true
  defaultVolumesToFsBackup: true
  hooks:
    resources:
      - name: postgres-backup-hook
        includedNamespaces:
          - production
        includedResources:
          - pods
        labelSelector:
          matchLabels:
            app: postgres
        pre:
          - exec:
              container: postgres
              command:
                - /bin/sh
                - -c
                - "PGPASSWORD=$POSTGRES_PASSWORD pg_dump -U postgres mydb > /tmp/dump.sql"
```

## Stash: Application-Aware Backup Operator

[Stash](https://github.com/stashed/stash), developed by AppsCode, takes a different philosophy. Instead of backing up entire cluster state, Stash focuses on **application-level backup** — it integrates directly into the workload's pod and backs up only the data that matters.

### How Stash Works

Stash uses Kubernetes operators and Custom Resource Definitions (CRDs) to manage backups. When you create a `BackupConfiguration` resource, Stash injects a sidecar container (running Restic or Kopia) into your target pod. This sidecar performs incremental backups directly from within the pod's network namespace, eliminating the need for a separate backup DaemonSet.

Stash supports a wide range of backends: S3-compatible object storage, Google Cloud Storage, Azure Blob Storage, Backblaze B2, Restic repositories, and SFTP servers.

### Installing Stash via Helm

```bash
# Add the AppsCode Helm repository
helm repo add appscode https://charts.appscode.com/stable/
helm repo update

# Install Stash Community (open-source) edition
helm install stash appscode/stash \
  --version v2024.12.19 \
  --namespace stash \
  --create-namespace \
  --set features.community=true \
  --set global.license=""

# For the Enterprise edition, provide your license:
# --set global.license="your-license-key"
```

### Defining a Backup Backend

```yaml
apiVersion: stash.appscode.com/v1beta1
kind: Repository
metadata:
  name: minio-repo
  namespace: production
spec:
  backend:
    s3:
      endpoint: http://minio:9000
      bucket: stash-backups
      prefix: /production/postgres
    storageSecretName: minio-cred
  usagePolicy:
    allowedNamespaces:
      from: Same
```

### Creating a BackupConfiguration

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
      apiVersion: apps/v1
      kind: StatefulSet
      name: postgres
    volumeMounts:
      - name: postgres-data
        mountPath: /var/lib/postgresql/data
    paths:
      - /var/lib/postgresql/data
  retentionPolicy:
    name: "keep-last-30-daily"
    keepLast: 30
    keepDaily: 30
    prune: true
```

### The Stash Restore Process

```yaml
apiVersion: stash.appscode.com/v1beta1
kind: RestoreSession
metadata:
  name: postgres-restore
  namespace: production
spec:
  repository:
    name: minio-repo
  task:
    name: postgres-restore-17
  target:
    ref:
      apiVersion: apps/v1
      kind: StatefulSet
      name: postgres
    volumeMounts:
      - name: postgres-data
        mountPath: /var/lib/postgresql/data
    rules:
      - paths:
          - /var/lib/postgresql/data
```

## VolSync: Volume-Centric Replication and Sync

[VolSync](https://github.com/backube/volsync) takes a fundamentally different approach. Instead of backing up full cluster state or individual applications, VolSync focuses exclusively on **PersistentVolume replication and synchronization**. It's designed for scenarios where you need to replicate data between clusters, storage backends, or PVCs on a schedule.

VolSync is part of the OpenShift Data Foundation (ODF) ecosystem but works on any Kubernetes cluster.

### How VolSync Works

VolSync uses two primary CRDs:

- **ReplicationSource** — defines what to back up (a source PVC) and where to send it
- **ReplicationDestination** — defines where to receive replicated data

Unlike Velero and Stash, VolSync does not back up Kubernetes resources (Deployments, Services, etc.). It's purely a volume replication tool, which makes it simpler but also more limited in scope.

### Installing VolSync via Helm

```bash
# Add the backube Helm repository
helm repo add backube https://backube.github.io/helm-charts/
helm repo update

# Install VolSync
helm install volsync backube/volsync \
  --namespace volsync-system \
  --create-namespace \
  --set manageCRDs=true
```

### Creating a ReplicationSource (Backup to S3)

```yaml
apiVersion: volsync.backube/v1alpha1
kind: ReplicationSource
metadata:
  name: postgres-rsync
  namespace: production
spec:
  sourcePVC: postgres-data
  trigger:
    schedule: "0 2 * * *"
  restic:
    repository: restic-secret
    pruneIntervalDays: 7
    retain:
      daily: 7
      weekly: 4
    moverSecurityContext:
      runAsUser: 26
      runAsGroup: 26
      fsGroup: 26
    cacheCapacity: 2Gi
    cacheStorageClassName: standard
```

### ReplicationSecret for S3 Storage

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: restic-secret
  namespace: production
type: Opaque
stringData:
  RESTIC_REPOSITORY: s3:http://minio:9000/volsync-backups/postgres
  RESTIC_PASSWORD: "my-restic-password"
  AWS_ACCESS_KEY_ID: "minioadmin"
  AWS_SECRET_ACCESS_KEY: "minioadmin"
```

### ReplicationDestination (Restore / Cross-Cluster Sync)

```yaml
apiVersion: volsync.backube/v1alpha1
kind: ReplicationDestination
metadata:
  name: postgres-restore
  namespace: production
spec:
  trigger:
    manual: restore-once
  restic:
    repository: restic-secret
    copyMethod: Direct
    volumeSnapshotClassName: csi-snapclass
    storageClassName: standard
    accessModes:
      - ReadWriteOnce
    capacity: 10Gi
```

## Choosing the Right Tool

### Pick Velero if:

- You need **full cluster backup and disaster recovery** (resources + PVs)
- You plan to **migrate workloads between clusters**
- You want a single tool that handles both stateless resources and stateful data
- Your CSI driver supports VolumeSnapshots for fast PV backups
- You need pre/post hooks for database dumps before backup

### Pick Stash if:

- You want **application-aware backup** integrated at the pod level
- Your team already uses AppsCode products (Kubedb, Stash Enterprise)
- You need fine-grained backup policies per application
- You prefer **sidecar injection** over DaemonSet-based filesystem backup
- You want Kopia as a backup engine option alongside Restic

### Pick VolSync if:

- You only need **volume-level replication** (not full cluster state)
- You are replicating data **between clusters** or storage backends
- You're on OpenShift and want native ODF integration
- You need asynchronous replication with configurable RPO
- Your backup target is another PVC (PVC-to-PVC sync)

## Disaster Recovery Architecture

A production-grade self-hosted Kubernetes disaster recovery plan typically combines tools rather than relying on a single solution:

```
┌─────────────────────────────────────────────────┐
│                 Primary Cluster                  │
│                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐ │
│  │ Velero   │──▶│ MinIO/S3 │   │  Stash or    │ │
│  │(cluster  │   │  (off-   │◀──│  VolSync     │ │
│  │ state +  │   │ cluster) │   │ (app-level / │ │
│  │ PVs)     │   │          │   │  volume)     │ │
│  └──────────┘   └──────────┘   └──────────────┘ │
└─────────────────────────────────────────────────┘
                      │
                      │ sync
                      ▼
┌─────────────────────────────────────────────────┐
│               DR Cluster (passive)               │
│  ┌──────────┐   ┌──────────────────────────────┐ │
│  │ Velero   │   │ VolSync ReplicationDestination│ │
│  │ restore  │──▶│ (auto-replicated PVCs)       │ │
│  └──────────┘   └──────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

The pattern: use Velero for periodic full-cluster snapshots (your ultimate fallback), and layer Stash or VolSync for frequent, application-specific backups with faster RPOs. Store all backups on an off-cluster MinIO or S3-compatible target — [setting up MinIO](../minio-self-hosted-s3-object-storage-guide-2026/) is straightforward and gives you full control over your backup storage.

## Backup Strategy Best Practices

1. **Follow the 3-2-1 rule**: Keep at least 3 copies of your data, on 2 different storage types, with 1 copy off-site. For Kubernetes, this means: active PVCs, cluster-local snapshots, and off-cluster object storage.

2. **Test restores regularly**: A backup you cannot restore is not a backup. Schedule periodic restore drills to a staging namespace. See our [backup verification guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/) for automated integrity testing strategies.

3. **Separate resource and data backups**: Kubernetes resource manifests (YAML) are small and fast to back up. PV data is large and slow. Velero handles both; VolSync handles only data. Choose based on your RTO/RPO requirements.

4. **Use CSI snapshots when available**: CSI-native snapshots are instant and don't copy data during backup. Velero leverages this automatically. Restic/Kopia filesystem backup is slower but works with any CSI driver.

5. **Encrypt your backup data**: Both Restic and Kopia encrypt data client-side before uploading. Always set a strong `RESTIC_PASSWORD`. If using Velero with CSI snapshots, ensure your storage backend supports encryption at rest.

6. **Version your backup tool**: Pin your Helm chart version. Velero, Stash, and VolSync all introduce breaking CRD changes between major versions. Test upgrades on a non-production cluster first.

For database-specific backup strategies (PostgreSQL, MySQL), dedicated tools like the ones covered in our [PostgreSQL backup comparison](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/) provide more granular control than general-purpose Kubernetes backup tools.

## FAQ

### Can Velero, Stash, and VolSync be used together?

Yes. In fact, this is a recommended pattern for production environments. Velero handles full cluster state and resource backup (Deployments, Services, ConfigMaps, Secrets), while Stash or VolSync provides frequent, application-level or volume-level backups with tighter RPOs. They do not conflict because they operate on different CRD namespaces and target different scopes.

### Does Velero support Restic and Kopia?

Velero originally used Restic for filesystem backup and added Kopia support in version 1.12. Both are available as plugins. Kopia is generally faster for incremental backups due to its content-addressable storage and better deduplication. Enable filesystem backup with `--set configuration.defaultVolumesToFsBackup=true` in your Helm values.

### Which tool is best for multi-cluster replication?

VolSync is purpose-built for this scenario. Its `ReplicationSource` and `ReplicationDestination` CRDs are designed for asynchronous volume replication between clusters, with configurable schedules and retention policies. Velero can migrate data between clusters via shared object storage, but it is not designed for continuous replication.

### Do any of these tools support encrypted backups?

Yes. Stash (via Restic/Kopia) and VolSync (via Restic) both encrypt data client-side before it leaves the cluster. The `RESTIC_PASSWORD` (or Kopia passphrase) is the encryption key — if you lose it, your backup data is unrecoverable. Velero with CSI snapshots relies on the storage provider's encryption; filesystem backup via Restic/Kopia adds client-side encryption.

### Can I restore individual files from a backup?

Stash and VolSync (via Restic) support browsing and restoring individual files from backup snapshots using the `stash restore` command or `restic mount` for FUSE-based access. Velero's restore is namespace or resource-level — it does not support single-file restore from PV backups. For file-level recovery, Stash or VolSync is the better choice.

### What happens if my backup storage (S3/MinIO) goes down?

Backups queued during storage unavailability will fail and be retried according to the tool's retry policy. Velero retries failed backups automatically. Stash marks failed BackupConfigurations with status conditions. VolSync ReplicationSources will retry on the next scheduled trigger. Ensure your object storage has its own redundancy (e.g., MinIO erasure coding across multiple nodes).

### How do I back up etcd alongside these tools?

None of these tools back up etcd — they back up Kubernetes resources via the API server. etcd backup is a separate concern. Use `etcdctl snapshot save` for etcd backups, and store the snapshot file in the same object storage as your Velero/Stash backups. For a complete etcd backup strategy, refer to your distribution's documentation.

### Are these tools compatible with all Kubernetes distributions?

Velero works with most distributions (kubeadm, k3s, EKS, GKE, AKS, OpenShift). Stash works similarly but has better documentation for AppsCode's own distributions. VolSync is officially part of OpenShift Data Foundation but works on any cluster with the external-snapshotter CRDs installed. Test on your specific distribution before production deployment.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Velero vs Stash vs VolSync: Kubernetes Backup Orchestration Guide 2026",
  "description": "Compare Velero, Stash, and VolSync for self-hosted Kubernetes backup orchestration. Features, Helm install guides, CRD comparisons, and disaster recovery strategies.",
  "datePublished": "2026-04-19",
  "dateModified": "2026-04-19",
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
