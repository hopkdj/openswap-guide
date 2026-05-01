---
title: "Self-Hosted etcd Backup & Disaster Recovery: Complete Guide (2026)"
date: 2026-05-02
tags: ["guide", "self-hosted", "kubernetes", "database", "backup", "disaster-recovery"]
draft: false
description: "Complete guide to backing up, restoring, and performing disaster recovery for etcd clusters. Covers snapshots, automated backup tools, and production-tested recovery procedures."
---

etcd is the backbone of every Kubernetes cluster — it stores all cluster state, configuration data, and secrets. If your etcd data is lost, your entire Kubernetes cluster becomes unrecoverable. Yet many operators rely solely on etcd's built-in snapshot capability without a comprehensive backup strategy.

This guide covers every aspect of etcd backup and disaster recovery: manual snapshots, automated backup tools, off-site storage, cluster restoration procedures, and production-tested best practices to ensure your cluster state is always recoverable.

## Why etcd Backup Matters

etcd stores everything that makes your Kubernetes cluster function:

- **Pod and service definitions** — every deployment, service, ingress, and configmap
- **Secrets and certificates** — TLS certs, API tokens, database credentials
- **RBAC policies** — role bindings, service accounts, cluster roles
- **CRD data** — custom resource definitions and their instances
- **Cluster state** — node status, endpoint mappings, lease information

Without a backup, a disk failure or operator error on etcd means rebuilding your cluster from scratch and re-deploying every workload manually.

For Kubernetes disaster recovery strategies, see our [Kanister vs K8up vs Stash guide](../2026-05-02-kanister-vs-k8up-vs-stash-kubernetes-disaster-recovery-guide/) which covers broader cluster-level backup solutions.

## Quick Comparison: etcd Backup Tools

| Tool | Method | Schedule | Off-site | Restore | Min. etcd Version |
|---|---|---|---|---|---|
| **etcdctl snapshot** | CLI manual | Manual | Via rsync/cron | Full cluster | 3.0+ |
| **etcd-backup-operator** | Kubernetes Operator | Cron-based | S3/GCS | Full cluster | 3.2+ |
| **Velero etcd plugin** | Velero integration | Cron-based | S3/GCS/Azure | Full cluster | 3.3+ |
| **kubeadm backup** | kubeadm etcd | Manual | Via copy | Full cluster | 3.4+ |
| **Automated cron** | Systemd timer | Scheduled | S3/rsync | Full cluster | Any |

## Method 1: Manual Snapshots with etcdctl

The simplest and most reliable method — using etcd's built-in snapshot capability.

### Taking a Snapshot

```bash
# Single-node etcd
ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +%Y%m%d).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Verify snapshot integrity
ETCDCTL_API=3 etcdctl snapshot status /backup/etcd-snapshot-$(date +%Y%m%d).db \
  --write-out=table
```

Output shows snapshot size, hash, and total key count:

```
+----------+----------+------------+------------+
|   HASH   | REVISION | TOTAL KEYS | TOTAL SIZE |
+----------+----------+------------+------------+
| 8c2a1b3d |   145892 |       5421 |    18 MB   |
+----------+----------+------------+------------+
```

### Automated Snapshot via Cron

```bash
# Add to root crontab
0 */6 * * * ETCDCTL_API=3 etcdctl snapshot save /backup/etcd-snapshot-$(date +\%Y\%m\%d-\%H).db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key \
  && find /backup/etcd-snapshot-*.db -mtime +7 -delete
```

This takes a snapshot every 6 hours and removes backups older than 7 days.

### Restoring from a Snapshot

```bash
# Stop the etcd service
systemctl stop etcd

# Restore from snapshot
ETCDCTL_API=3 etcdctl snapshot restore /backup/etcd-snapshot-20260502.db \
  --data-dir=/var/lib/etcd-restore \
  --name=etcd-node1 \
  --initial-cluster=etcd-node1=https://10.0.1.10:2380 \
  --initial-advertise-peer-urls=https://10.0.1.10:2380

# Replace the data directory
mv /var/lib/etcd /var/lib/etcd-old
mv /var/lib/etcd-restore /var/lib/etcd
chown -R etcd:etcd /var/lib/etcd

# Start etcd
systemctl start etcd
```

## Method 2: etcd-backup-operator

The [etcd-backup-operator](https://github.com/giantswarm/etcd-backup-operator) runs as a Kubernetes operator and manages automated backups with configurable schedules and S3/GCS storage.

### Installation

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: etcd-backup
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: etcd-backup-operator
  namespace: etcd-backup
spec:
  replicas: 1
  selector:
    matchLabels:
      app: etcd-backup-operator
  template:
    metadata:
      labels:
        app: etcd-backup-operator
    spec:
      serviceAccountName: etcd-backup-sa
      containers:
        - name: operator
          image: giantswarm/etcd-backup-operator:latest
          env:
            - name: AWS_ACCESS_KEY_ID
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: access-key
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  name: s3-credentials
                  key: secret-key
```

### Backup Schedule Configuration

```yaml
apiVersion: "etcdbackup.giantswarm.io/v1alpha1"
kind: EtcdBackup
metadata:
  name: daily-etcd-backup
  namespace: etcd-backup
spec:
  etcdEndpoints:
    - https://10.0.1.10:2379
    - https://10.0.1.11:2379
    - https://10.0.1.12:2379
  backupInterval: 24h
  backupLimit: 30
  s3Bucket: k8s-etcd-backups
  s3Path: /production/etcd/
  tlsSecret: etcd-client-certs
```

### S3 Credentials Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: s3-credentials
  namespace: etcd-backup
type: Opaque
data:
  access-key: <base64-encoded-access-key>
  secret-key: <base64-encoded-secret-key>
```

## Method 3: Velero Integration

Velero is a popular Kubernetes backup tool that can include etcd snapshots as part of full cluster backups.

### Install Velero with etcd Plugin

```bash
velero install \
  --provider aws \
  --bucket k8s-backups \
  --backup-location-config region=us-east-1,s3ForcePathStyle=true,s3Url=https://s3.example.com \
  --secret-file ./velero-credentials \
  --use-volume-snapshots=false
```

### Create a Backup Schedule

```bash
# Backup everything including etcd every 12 hours
velero schedule create full-cluster \
  --schedule="0 */12 * * *" \
  --ttl 720h \
  --include-cluster-resources=true

# Create an on-demand backup
velero backup create etcd-manual --include-cluster-resources=true
```

### Restore a Cluster

```bash
# Restore the most recent backup
velero restore create --from-backup full-cluster-20260502

# Restore a specific backup
velero restore create --from-backup full-cluster-20260501-120000
```

## Method 4: Automated Cron with Systemd Timer

For non-Kubernetes etcd deployments or when you want OS-level backup scheduling:

### Systemd Timer Unit

```ini
# /etc/systemd/system/etcd-backup.timer
[Unit]
Description=etcd Backup Timer

[Timer]
OnCalendar=*-*-* 00/6:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### Systemd Service Unit

```ini
# /etc/systemd/system/etcd-backup.service
[Unit]
Description=etcd Backup Service
After=etcd.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/etcd-backup.sh
EnvironmentFile=/etc/default/etcd-backup
```

### Backup Script

```bash
#!/bin/bash
# /usr/local/bin/etcd-backup.sh
set -euo pipefail

BACKUP_DIR="/backup/etcd"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

mkdir -p "${BACKUP_DIR}"

# Take snapshot
ETCDCTL_API=3 etcdctl snapshot save "${BACKUP_DIR}/etcd-${TIMESTAMP}.db" \
  --endpoints="${ETCD_ENDPOINTS}" \
  --cacert="${ETCD_CACERT}" \
  --cert="${ETCD_CERT}" \
  --key="${ETCD_KEY}"

# Verify snapshot
ETCDCTL_API=3 etcdctl snapshot status "${BACKUP_DIR}/etcd-${TIMESTAMP}.db" \
  --write-out=table

# Upload to off-site storage
aws s3 cp "${BACKUP_DIR}/etcd-${TIMESTAMP}.db" \
  "s3://${S3_BUCKET}/etcd/etcd-${TIMESTAMP}.db"

# Clean up old local backups
find "${BACKUP_DIR}" -name "etcd-*.db" -mtime +${RETENTION_DAYS} -delete

echo "Backup completed: etcd-${TIMESTAMP}.db"
```

## Multi-Node Cluster Backup Considerations

For etcd clusters with 3 or 5 nodes:

1. **Backup from one node only**: Snapshots are consistent across the cluster — you only need to back up one member
2. **Rotate the backup source**: Periodically back up from different nodes to catch any replication lag
3. **Test restore to a new cluster**: Periodically verify your backups by restoring to a fresh environment
4. **Monitor snapshot size**: A sudden increase in snapshot size may indicate a runaway controller creating too many objects

```bash
# Monitor snapshot size over time
ls -lh /backup/etcd/etcd-*.db | awk '{print $5, $9}' | sort -k2
```

## Disaster Recovery Scenarios

### Scenario 1: Single Node Failure

If one etcd node in a 3-node cluster fails:

```bash
# Remove the failed member
etcdctl member list
etcdctl member remove <failed-member-id>

# Add a new member
etcdctl member add etcd-node3 \
  --peer-urls=https://10.0.1.13:2380

# Start etcd on the new node with --initial-cluster-state=existing
```

### Scenario 2: Complete Cluster Loss

When all etcd nodes are unrecoverable:

1. Stop all Kubernetes control plane components
2. Restore etcd from the latest snapshot on a new node (see Method 1 restore steps)
3. Restart the API server, controller manager, and scheduler
4. Verify cluster state: `kubectl get nodes` and `kubectl get pods --all-namespaces`

### Scenario 3: Corrupted Data

If etcd data is corrupted but the service is still running:

```bash
# Take an immediate snapshot before attempting any repair
ETCDCTL_API=3 etcdctl snapshot save /backup/emergency-snapshot.db \
  --endpoints=https://127.0.0.1:2379 \
  --cacert=/etc/kubernetes/pki/etcd/ca.crt \
  --cert=/etc/kubernetes/pki/etcd/server.crt \
  --key=/etc/kubernetes/pki/etcd/server.key

# Then proceed with restore from a known-good snapshot
```

## Best Practices

1. **Backup at least every 6 hours**: etcd changes rapidly; a 24-hour backup window risks significant data loss
2. **Store off-site**: Never keep backups on the same server as etcd — use S3, GCS, or a separate NFS share
3. **Test restores quarterly**: A backup you haven't tested is not a backup
4. **Encrypt backups at rest**: etcd contains secrets — encrypt backup files with age or GPG before uploading
5. **Monitor backup success**: Set up alerts for failed backup jobs — silent backup failures are worse than no backups
6. **Keep at least 30 days of history**: This covers delayed discovery of issues and provides multiple restore points
7. **Document the restore procedure**: In a disaster, your team needs clear, tested instructions — not wiki pages they hope are current

For broader Kubernetes backup strategies that cover application data alongside etcd, see our [Velero vs Stash vs Volsync guide](../velero-vs-stash-vs-volsync-kubernetes-backup-orchestration-guide/).

## FAQ

### How often should I back up etcd?
At minimum every 6 hours. In high-change environments (CI/CD clusters with frequent deployments), every 1-2 hours is recommended. etcd snapshots are fast (typically 1-5 seconds) and have minimal performance impact.

### Can I back up etcd while it is running?
Yes. etcd snapshots are consistent point-in-time captures that work on a live cluster. The `etcdctl snapshot save` command is safe to run during normal operations and does not require stopping etcd.

### How large are etcd snapshots?
For a typical Kubernetes cluster with 100-500 pods, snapshots range from 10-50 MB. Very large clusters with thousands of resources may produce 100-500 MB snapshots. The size correlates with the number of keys in etcd, not the number of nodes.

### What happens if I restore an old etcd snapshot?
Restoring an old snapshot rolls back all cluster state to that point in time. Any resources created, modified, or deleted after the snapshot will be lost. Always restore the most recent verified snapshot, and be prepared to re-apply any changes made since the backup.

### Should I encrypt etcd backups?
Absolutely. etcd stores Kubernetes Secrets in plaintext (unless you use encryption at rest, which many clusters don't). Backup files contain all your secrets, TLS certificates, and service account tokens. Always encrypt backups with a tool like `age` before storing them off-site.

### How do I verify an etcd backup is valid?
Run `etcdctl snapshot status <backup-file> --write-out=table` to check the snapshot's hash, revision, total keys, and total size. A valid snapshot will display these values. You can also test by restoring to a temporary directory and running `etcdctl get / --prefix --keys-only` to list all keys.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted etcd Backup & Disaster Recovery: Complete Guide (2026)",
  "description": "Complete guide to backing up, restoring, and performing disaster recovery for etcd clusters. Covers snapshots, automated backup tools, and production-tested recovery procedures.",
  "datePublished": "2026-05-02",
  "dateModified": "2026-05-02",
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
