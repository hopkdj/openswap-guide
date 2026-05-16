---
title: "Self-Hosted ClickHouse Kubernetes Operations: Altinity Operator vs Official Operator vs clickhouse-backup"
date: "2026-05-16"
tags: ["clickhouse", "kubernetes", "database-operations", "kubernetes-operator", "olap"]
draft: false
---

ClickHouse has become the go-to OLAP database for real-time analytics, log processing, and time-series workloads. Deploying ClickHouse on Kubernetes brings scalability and resilience, but managing ClickHouse clusters at scale requires specialized tooling. This guide compares three essential tools for self-hosted ClickHouse operations on Kubernetes: the **Altinity Kubernetes Operator**, the **Official ClickHouse Operator**, and **clickhouse-backup** for disaster recovery.

## Why Self-Host ClickHouse on Kubernetes

Running ClickHouse on Kubernetes solves several operational challenges at once. It automates cluster provisioning, handles node failures gracefully, enables horizontal scaling of shards and replicas, and integrates with Kubernetes-native monitoring and alerting pipelines.

Self-hosting ClickHouse on your own Kubernetes cluster — rather than using a managed service — gives you full control over data locality, compliance boundaries, and cost optimization. For organizations processing sensitive analytics data, keeping the entire data pipeline within their own infrastructure is often a regulatory requirement.

For ClickHouse web-based management interfaces, see our [ClickHouse management UIs guide](../2026-05-13-self-hosted-clickhouse-management-uis-tabix-clickcat-telescope-guide/). For broader Kubernetes operator frameworks, check our [operator frameworks comparison](../2026-05-01-operator-sdk-vs-kubebuilder-vs-java-operator-sdk-kubernetes-operator-frameworks/). And for PostgreSQL operators on Kubernetes, our [PostgreSQL operators guide](../2026-05-10-self-hosted-postgresql-operators-cloudnativepg-zalando-crunchydata-guide/) covers similar patterns for OLTP workloads.

The operational overhead of managing ClickHouse manually — provisioning servers, configuring ZooKeeper or ClickHouse Keeper, handling schema migrations, managing backups, and monitoring cluster health — grows rapidly as your deployment scales. Kubernetes operators abstract these complexities into declarative configuration, allowing platform teams to manage ClickHouse clusters the same way they manage any other Kubernetes workload.

Self-hosting ClickHouse on your own Kubernetes cluster also avoids vendor lock-in and data egress costs. For organizations processing terabytes of analytics data daily, the cost of managed ClickHouse services can exceed the operational cost of running your own cluster — especially when you factor in data transfer charges and the premium for managed SLAs.

The backup story is equally important. ClickHouse's native backup capabilities are limited compared to what dedicated backup tools provide. Without a tool like clickhouse-backup, you're left with file-level snapshots that don't capture the full state of tables, dictionaries, and user configurations. Incremental backups, encryption, and cross-cluster restore capabilities are essential for production analytics workloads but are not available through operators alone.

For teams managing multiple analytical databases, the pattern of using a Kubernetes operator for lifecycle management alongside a dedicated backup tool is well-established. It mirrors how PostgreSQL operators (like CloudNativePG) work alongside pgBackRest, or how MongoDB operators pair with dedicated backup solutions. Separating concerns between cluster management and disaster recovery is a proven operational pattern.

## Comparison Overview

| Feature | Altinity Operator | Official CH Operator | clickhouse-backup |
|---------|-------------------|---------------------|-------------------|
| GitHub Stars | 2,503+ | 238+ | 1,601+ |
| Primary Focus | Full cluster lifecycle | Cluster provisioning | Backup & restore |
| Kubernetes Native | Yes (CRD-based) | Yes (CRD-based) | No (standalone binary) |
| Multi-Cluster | Yes | No | No |
| Auto-Scaling | Yes (vertical + horizontal) | Basic | N/A |
| Backup Integration | Via clickhouse-backup | Manual | Native |
| Storage Types | Any PVC | Any PVC | S3, GCS, Azure Blob, FTP, local |
| Incremental Backup | Via clickhouse-backup | No | Yes |
| Schema Migration | Manual | Manual | Preserves schema |
| Monitoring | Prometheus metrics | Prometheus metrics | CLI status output |
| Upgrade Strategy | Rolling, canary | Rolling | N/A |
| Cloud Support | AWS, GCP, Azure | Generic Kubernetes | Any S3-compatible |
| Best For | Production clusters | Simple deployments | Disaster recovery |

## Altinity Kubernetes Operator — Production-Grade ClickHouse Management

The **Altinity Kubernetes Operator** is the most mature and feature-complete solution for managing ClickHouse on Kubernetes. Developed by Altinity, a company with deep ClickHouse expertise, it provides comprehensive cluster lifecycle management.

### Key Features

- **Declarative configuration**: Define entire ClickHouse topologies in YAML
- **Auto-scaling**: Scale shards and replicas independently
- **Zero-downtime upgrades**: Rolling updates with configurable strategies
- **Persistent storage management**: Automatic PVC provisioning and resizing
- **Multi-cluster support**: Replicate across Kubernetes clusters
- **Custom resource definitions**: Full CRD-based management
- **Integration**: Works with Prometheus, Grafana, and ClickHouse Keeper

### Kubernetes Manifest

```yaml
apiVersion: "clickhouse.altinity.com/v1"
kind: "ClickHouseInstallation"
metadata:
  name: "production-analytics"
spec:
  defaults:
    templates:
      podTemplate: clickhouse-pod
      volumeClaimTemplate: storage-claim
  configuration:
    users:
      admin/password: "strong-password-here"
      admin/profile: "default"
      admin/networks/ip: "10.0.0.0/8"
    clusters:
      - name: "analytics-cluster"
        layout:
          shardsCount: 3
          replicasCount: 2
        templates:
          podTemplate: clickhouse-pod
  templates:
    podTemplates:
      - name: clickhouse-pod
        spec:
          containers:
            - name: clickhouse
              image: "clickhouse/clickhouse-server:24.8"
              resources:
                requests:
                  memory: "4Gi"
                  cpu: "2"
                limits:
                  memory: "8Gi"
                  cpu: "4"
    volumeClaimTemplates:
      - name: storage-claim
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 100Gi
```

### Installation

```bash
# Install the operator via Helm
helm repo add altinity https://docs.altinity.com/clickhouse-operator/
helm install clickhouse-operator altinity/clickhouse-operator

# Or install via kubectl
kubectl apply -f https://raw.githubusercontent.com/Altinity/clickhouse-operator/master/deploy/operator.yaml

# Verify installation
kubectl get pods -n kube-system | grep clickhouse-operator
```

## Official ClickHouse Kubernetes Operator — Simplicity First

The **Official ClickHouse Operator** (from ClickHouse, Inc.) provides a streamlined approach to deploying ClickHouse clusters on Kubernetes. It focuses on the essential operations: provisioning, scaling, and basic lifecycle management.

### Key Features

- **Simple deployment**: Minimal configuration for quick setup
- **Official support**: Maintained by ClickHouse, Inc.
- **Standard CRDs**: Follows Kubernetes operator best practices
- **Shard management**: Automatic shard and replica configuration
- **Resource management**: CPU and memory limits per pod

### Kubernetes Manifest

```yaml
apiVersion: "clickhouse-keeper.altinity.com/v1"
kind: "ClickHouseInstallation"
metadata:
  name: "simple-analytics"
spec:
  configuration:
    clusters:
      - name: "cluster"
        layout:
          shardsCount: 2
          replicasCount: 1
    settings:
      default_profile: "default"
  templates:
    podTemplates:
      - name: clickhouse-pod
        spec:
          containers:
            - name: clickhouse
              image: clickhouse/clickhouse-server:24.8
              resources:
                limits:
                  cpu: "2"
                  memory: "4Gi"
```

### Installation

```bash
# Install via kubectl
kubectl apply -f https://raw.githubusercontent.com/ClickHouse/clickhouse-operator/master/deploy/operator.yaml

# Apply your CHI manifest
kubectl apply -f clickhouse-installation.yaml

# Check cluster status
kubectl get chi
```

## clickhouse-backup — Disaster Recovery for ClickHouse

**clickhouse-backup** by Altinity is a dedicated backup and restore tool for ClickHouse. It handles full and incremental backups, supports multiple storage backends, and integrates seamlessly with both operators.

### Key Features

- **Incremental backups**: Only backup changed data since last backup
- **Multiple storage backends**: S3, GCS, Azure Blob Storage, FTP, SFTP, local disk
- **Schema preservation**: Backs up table schemas along with data
- **Cross-cluster restore**: Restore backups to different ClickHouse clusters
- **Encryption**: AES-256 encryption for backup data at rest
- **Compression**: Configurable compression (lz4, gzip, zstd, brotli)
- **Parallel operations**: Multi-threaded backup and restore

### Docker Compose Deployment (Sidecar Pattern)

```yaml
version: "3.8"
services:
  clickhouse-backup:
    image: altinity/clickhouse-backup:latest
    environment:
      - CLICKHOUSE_HOST=clickhouse-server
      - CLICKHOUSE_PORT=9000
      - CLICKHOUSE_USERNAME=default
      - CLICKHOUSE_PASSWORD=
      - S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - S3_SECRET_KEY=${S3_SECRET_KEY}
      - S3_BUCKET=clickhouse-backups
      - S3_REGION=us-east-1
    volumes:
      - ./backup-config.yml:/etc/clickhouse-backup/config.yml
    command: server
    restart: unless-stopped

  clickhouse-server:
    image: clickhouse/clickhouse-server:24.8
    ports:
      - "8123:8123"
      - "9000:9000"
    volumes:
      - clickhouse-data:/var/lib/clickhouse
    restart: unless-stopped

volumes:
  clickhouse-data:
```

### Usage Commands

```bash
# Create a full backup
clickhouse-backup create full_backup_$(date +%Y%m%d)

# Create an incremental backup
clickhouse-backup create incremental_$(date +%Y%m%d)

# Upload to remote storage
clickhouse-backup upload full_backup_20260524

# List available backups
clickhouse-backup list

# Restore a backup
clickhouse-backup restore full_backup_20260524

# Delete old backups
clickhouse-backup delete local full_backup_20260500
```

## Choosing the Right ClickHouse Operations Stack

For a complete ClickHouse operations setup on Kubernetes:

- **Use the Altinity Operator** as your primary cluster manager for production workloads. Its mature feature set, multi-cluster support, and integration ecosystem make it the best choice for teams running ClickHouse at scale.

- **Use the Official Operator** for simpler deployments, testing environments, or when you want to stay close to ClickHouse, Inc.'s recommended stack. It's lightweight and gets you running quickly.

- **Use clickhouse-backup** alongside either operator for disaster recovery. No operator handles backup natively with the depth that clickhouse-backup provides. Schedule regular incremental backups to S3 or equivalent object storage.

## FAQ

### Can I use clickhouse-backup with the Official ClickHouse Operator?

Yes. clickhouse-backup is a standalone tool that connects to any running ClickHouse server via the native TCP port (9000) or HTTP port (8123). It does not depend on any specific Kubernetes operator.

### Does the Altinity Operator support automatic failover?

Yes. The Altinity Operator manages ClickHouse Keeper (or ZooKeeper) for coordination between replicas. If a replica pod fails, Kubernetes restarts it, and ClickHouse Keeper ensures data consistency across the cluster.

### How do I monitor ClickHouse clusters managed by these operators?

Both operators expose Prometheus metrics from the ClickHouse pods. Deploy Prometheus and Grafana in your Kubernetes cluster, and use the official ClickHouse Grafana dashboards for monitoring query performance, storage usage, and cluster health.

### Can I migrate from the Official Operator to the Altinity Operator?

Migration is possible but requires careful planning. Both operators use similar CRD structures, but the Altinity operator has additional fields. Export your CHI manifests, update the API version and add Altinity-specific settings, then apply the updated manifests.

### What is the recommended backup schedule for ClickHouse?

For production analytics workloads, schedule full backups weekly and incremental backups daily. Use clickhouse-backup's built-in scheduler or Kubernetes CronJobs. Retain at least 4 weeks of incremental backups and 3 months of full backups.

### Does clickhouse-backup work with ClickHouse cloud deployments?

clickhouse-backup requires direct access to ClickHouse's native port (9000) or HTTP port (8123) with backup permissions. Cloud-hosted ClickHouse instances may restrict these ports. Check your provider's documentation for backup API support.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted ClickHouse Kubernetes Operations: Altinity Operator vs Official Operator vs clickhouse-backup",
  "description": "Compare three essential tools for self-hosted ClickHouse operations on Kubernetes — Altinity Operator for production management, Official Operator for simple deployments, and clickhouse-backup for disaster recovery.",
  "datePublished": "2026-05-16",
  "dateModified": "2026-05-16",
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
