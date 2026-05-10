---
title: "PostgreSQL Operators for Kubernetes: CloudNativePG vs Zalando vs CrunchyData"
date: "2026-05-10"
tags: ["kubernetes", "postgresql", "operators", "database", "cloudnativepg", "zalando", "crunchydata", "ha"]
draft: false
---

Running PostgreSQL in Kubernetes has evolved from manual StatefulSet management to sophisticated operator-based automation. PostgreSQL operators handle cluster lifecycle, automated failover, backups, replication, and scaling through custom Kubernetes resources. In this comprehensive comparison, we examine the three leading PostgreSQL operators: **CloudNativePG**, **Zalando Postgres Operator**, and **CrunchyData Postgres Operator** (PGO).

## Why Use a PostgreSQL Operator?

Deploying PostgreSQL manually in Kubernetes requires managing StatefulSets, Services, ConfigMaps, PersistentVolumeClaims, and custom scripts for replication and failover. Operators automate all of this by:

- **Automating cluster provisioning** — declare the desired cluster state, the operator handles the rest
- **Managing replication** — automatic streaming replication setup and monitoring
- **Handling failover** — automatic promotion of standby instances on primary failure
- **Scheduling backups** — built-in backup to S3, Azure Blob, or GCS with point-in-time recovery
- **Upgrading PostgreSQL** — rolling upgrades with zero downtime
- **Scaling read replicas** — declarative scaling of read-only instances

## CloudNativePG

[CloudNativePG](https://cloudnative-pg.io/) is a Kubernetes operator built by EDB (EnterpriseDB) that manages PostgreSQL clusters using a declarative API. It has become one of the most popular PostgreSQL operators, with over 8,500 GitHub stars.

### Architecture

CloudNativePG uses a single operator deployment that watches for `Cluster` custom resources. Each Cluster resource represents a full PostgreSQL HA cluster. The operator manages pods, services, and persistent volumes, using PostgreSQL's native streaming replication for data synchronization.

### Key Features

- **Declarative cluster management** — define your cluster in a single YAML resource
- **Automatic failover** — built-in with configurable failover policies
- **Integrated backups** — barman-based backups to object storage with PITR support
- **Rolling updates** — zero-downtime PostgreSQL version and configuration updates
- **Tablespace management** — declarative tablespace provisioning
- **Connection pooling** — optional PgBouncer sidecar for connection management
- **Monitoring** — native Prometheus metrics export

### Deployment

```bash
kubectl apply -f https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/release-1.24/releases/cnpg-1.24.0.yaml
```

Create a PostgreSQL cluster:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: production-db
spec:
  instances: 3
  imageName: ghcr.io/cloudnative-pg/postgresql:16.4
  storage:
    size: 50Gi
    storageClass: standard
  bootstrap:
    initdb:
      database: appdb
      owner: appuser
  backup:
    barmanObjectStore:
      destinationPath: "s3://my-bucket/backups/"
      endpointURL: "https://s3.amazonaws.com"
      s3Credentials:
        accessKeyId:
          name: aws-creds
          key: ACCESS_KEY_ID
        secretAccessKey:
          name: aws-creds
          key: ACCESS_SECRET_KEY
  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"
```

### Docker Compose (Local Testing)

For local development, the CloudNativePG operator can be tested with a simplified setup:

```yaml
version: "3.8"
services:
  postgres-primary:
    image: ghcr.io/cloudnative-pg/postgresql:16.4
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppassword
      POSTGRES_DB: appdb
    volumes:
      - primary-data:/var/lib/postgresql/data
    command: ["postgres", "-c", "wal_level=replica", "-c", "max_wal_senders=5"]

  postgres-standby:
    image: ghcr.io/cloudnative-pg/postgresql:16.4
    ports:
      - "5433:5432"
    environment:
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: apppassword
    depends_on:
      - postgres-primary
    volumes:
      - standby-data:/var/lib/postgresql/data
    command: >
      bash -c "pg_basebackup -h postgres-primary -U appuser -D /var/lib/postgresql/data -Fp -Xs -P -R &&
      exec postgres"

volumes:
  primary-data:
  standby-data:
```

## Zalando Postgres Operator

The [Zalando Postgres Operator](https://github.com/zalando/postgres-operator) is one of the oldest and most battle-tested PostgreSQL operators for Kubernetes, developed by Zalando SE. With over 5,100 stars, it has been running production workloads at Zalando for years.

### Architecture

The Zalando operator uses a configuration-driven approach. It watches for `postgresql` resources and manages StatefulSets, Services, and CronJobs for backups. It uses Patroni (a high-availability template for PostgreSQL) for managing replication and failover.

### Key Features

- **Patroni-based HA** — uses the proven Patroni framework for consensus-driven failover
- **Configuration flexibility** — extensive configuration options via the operator config map
- **Connection pooling** — integrated PgBouncer deployment per cluster
- **Logical backup jobs** — CronJob-based logical backups to S3
- **Standby clusters** — cross-cluster replication for disaster recovery
- **Team management** — database owner teams with RBAC integration
- **Sidecar support** — custom sidecar containers for monitoring and tooling

### Deployment

```bash
helm install postgres-operator postgres-operator/postgres-operator   --namespace postgres-operator   --create-namespace
```

Create a PostgreSQL cluster:

```yaml
apiVersion: "acid.zalan.do/v1"
kind: postgresql
metadata:
  name: acid-production
  namespace: default
spec:
  teamId: "acid"
  volume:
    size: 50Gi
    storageClass: standard
  numberOfInstances: 3
  users:
    appuser:
      - superuser
      - createdb
  databases:
    appdb: appuser
  postgresql:
    version: "16"
    parameters:
      shared_buffers: "512MB"
      max_connections: "200"
      wal_level: replica
  enableLogicalBackup: true
  logicalBackupSchedule: "00 01 * * *"
  sidecars:
    - name: pg-exporter
      image: prometheuscommunity/postgres-exporter:latest
      ports:
        - containerPort: 9187
```

## CrunchyData Postgres Operator (PGO)

[CrunchyData's Postgres Operator](https://github.com/CrunchyData/postgres-operator), also known as PGO, is developed by Crunchy Data, a company specializing in PostgreSQL. With over 4,400 stars, it offers enterprise-grade PostgreSQL management.

### Architecture

PGO uses custom resources (`PostgresCluster`) to define the desired state. It manages the full lifecycle including provisioning, backups, replication, failover, and updates. It uses PostgreSQL's native streaming replication and integrates with pgBackRest for backup management.

### Key Features

- **pgBackRest integration** — enterprise-grade backup with delta restore and encryption
- **Custom resource API** — declarative `PostgresCluster` resources
- **Automated TLS** — automatic certificate generation for encrypted connections
- **Standby clusters** — async replication to remote clusters for DR
- **PGO Dashboard** — web UI for cluster monitoring and management
- **PostGIS support** — native spatial database extensions
- **Encryption at rest** — encrypted volumes and backup encryption
- **Clone and restore** — point-in-time recovery and database cloning

### Deployment

```bash
kubectl apply -k https://github.com/CrunchyData/postgres-operator-examples/kustomize/install
```

Create a PostgreSQL cluster:

```yaml
apiVersion: postgres-operator.crunchydata.com/v1beta1
kind: PostgresCluster
metadata:
  name: hippo
  namespace: postgres-operator
spec:
  postgresVersion: 16
  instances:
    - name: instance1
      replicas: 2
      dataVolumeClaimSpec:
        accessModes:
          - "ReadWriteOnce"
        resources:
          requests:
            storage: 50Gi
  backups:
    pgbackrest:
      repos:
        - name: repo1
          s3:
            bucket: "my-backup-bucket"
            endpoint: "s3.amazonaws.com"
          schedules:
            full: "0 1 * * 0"
            differential: "0 1 * * 1-6"
  proxy:
    pgBouncer:
      replicas: 1
  monitoring:
    pgmonitor:
      exporter:
        resources:
          requests:
            cpu: 100m
            memory: 64Mi
          limits:
            cpu: 200m
            memory: 128Mi
```

## Feature Comparison

| Feature | CloudNativePG | Zalando Postgres Operator | CrunchyData PGO |
|---|---|---|---|
| GitHub Stars | 8,589 | 5,153 | 4,406 |
| License | Apache 2.0 | MIT | Apache 2.0 |
| HA Framework | Native streaming + K8s | Patroni | Native streaming + pgBackRest |
| Backup Engine | Barman | pg_dump (logical) / WAL-G | pgBackRest |
| Connection Pooling | PgBouncer (sidecar) | PgBouncer (integrated) | PgBouncer (built-in) |
| PITR Support | Yes | Yes (WAL-G) | Yes (pgBackRest) |
| Monitoring | Prometheus metrics | Prometheus + sidecars | pgMonitor + exporter |
| Web UI | No | No | PGO Dashboard |
| Cross-Cluster Rep | Yes (streaming) | Yes (standby clusters) | Yes (async replication) |
| PostgreSQL Versions | 12-17 | 12-17 | 12-17 |
| PostGIS Support | Yes | Yes | Yes (native) |
| Multi-Cluster Mgmt | Yes | Yes | Yes |
| Best For | Cloud-native teams | Patroni users | Enterprise PostgreSQL |

## Choosing the Right PostgreSQL Operator

- **Choose CloudNativePG** if you want a modern, cloud-native operator with a clean declarative API, built-in barman-based backups, and active community development. It's the fastest-growing operator and has strong backing from EDB.

- **Choose Zalando Postgres Operator** if you need the battle-tested Patroni framework for HA, have complex configuration requirements, or want extensive customization options. It has the longest production track record.

- **Choose CrunchyData PGO** if you want enterprise-grade features out of the box — pgBackRest backups, a management dashboard, PostGIS support, and comprehensive monitoring. Crunchy Data's PostgreSQL expertise shows in the operator's polish.

For related reading, see our [PostgreSQL backup guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide/) for deep coverage of backup strategies, and [database monitoring tools](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/) for monitoring PostgreSQL in production.

## Why Self-Host PostgreSQL on Kubernetes?

Running PostgreSQL on Kubernetes through an operator gives you the best of both worlds: the reliability and feature richness of PostgreSQL combined with the operational benefits of Kubernetes orchestration.

With an operator managing your PostgreSQL clusters, you get declarative infrastructure — define your database topology in YAML and let the operator handle the complexity. Automated failover means your database recovers from node failures without manual intervention. Scheduled backups with point-in-time recovery protect against data corruption and human error.

Self-hosting PostgreSQL on Kubernetes also gives you control over your data. Unlike managed database services (RDS, Cloud SQL), you decide the PostgreSQL version, configure parameters to your workload, install extensions like PostGIS, and avoid per-hour instance charges. For data-sensitive workloads, keeping your database within your own cluster boundary eliminates data transfer concerns.

Additionally, Kubernetes operators enable consistent database management across development, staging, and production environments. The same YAML that defines your production cluster can be adapted for lower environments, ensuring configuration parity.

For teams managing containerized databases, understanding [Kubernetes backup orchestration](../velero-vs-stash-vs-volsync-kubernetes-backup-orchestration-guide/) and [Kubernetes secrets management](../2026-04-20-external-secrets-operator-vs-sealed-secrets-vs-vault-secrets-operator-kubernetes-secrets-management-2026/) is essential for building resilient database infrastructure.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "PostgreSQL Operators for Kubernetes: CloudNativePG vs Zalando vs CrunchyData",
  "description": "Compare CloudNativePG, Zalando Postgres Operator, and CrunchyData PGO for running PostgreSQL on Kubernetes. Architecture, features, and deployment guides.",
  "datePublished": "2026-05-10",
  "dateModified": "2026-05-10",
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

### What is a Kubernetes operator?

A Kubernetes operator is a software extension that uses custom resources and controllers to manage applications and their components. For PostgreSQL, the operator automates deployment, configuration, scaling, backup, and recovery — tasks that would otherwise require manual intervention or custom scripts.

### Can I migrate from one PostgreSQL operator to another?

Yes, but it requires careful planning. The migration process typically involves: (1) setting up the new operator alongside the old one, (2) creating a standby cluster in the new operator that replicates from the existing primary, (3) verifying data consistency, (4) switching application connections to the new cluster, and (5) decommissioning the old operator. A physical backup/restore using pg_basebackup is the most reliable migration method.

### How do these operators handle PostgreSQL upgrades?

All three operators support rolling upgrades. CloudNativePG performs in-place upgrades by replacing pods one at a time. Zalando uses Patroni's switchover mechanism for minimal downtime. CrunchyData PGO performs rolling updates with pg_upgrade for major version upgrades. In all cases, the operator manages the complexity of data migration and configuration changes.

### Do I need an external backup storage for these operators?

Yes. All three operators require external storage (S3, Azure Blob, GCS, or compatible) for backups. The operator handles the backup process, but the actual backup data is stored externally to ensure recovery even if the entire Kubernetes cluster fails.

### Which operator is best for production workloads?

All three are production-grade. CloudNativePG has the fastest growth trajectory and cleanest API. Zalando has the longest production track record with Patroni-based reliability. CrunchyData PGO offers the most enterprise features. The best choice depends on your team's expertise, existing infrastructure, and specific requirements.

### Can these operators manage multiple PostgreSQL versions?

Yes. All three operators support running multiple PostgreSQL versions simultaneously in the same cluster. You can have a PostgreSQL 14 cluster managed by the same operator instance as a PostgreSQL 16 cluster, enabling gradual upgrades across your organization.
