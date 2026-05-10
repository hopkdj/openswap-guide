---
title: "Self-Hosted PostgreSQL Operators: CloudNativePG vs Zalando vs CrunchyData (2026)"
date: "2026-05-10"
tags: ["postgresql", "kubernetes", "operators", "database", "comparison", "self-hosted"]
draft: false
---

Running PostgreSQL in production on Kubernetes requires more than just deploying a container — you need automated backup, failover, scaling, and upgrades. PostgreSQL operators solve this by embedding database administration expertise directly into Kubernetes-native controllers.

In this guide, we compare the three leading open-source PostgreSQL operators: **CloudNativePG**, **Zalando Postgres Operator**, and **CrunchyData Postgres Operator**. Each takes a fundamentally different approach to managing PostgreSQL clusters on Kubernetes, and choosing the right one depends on your operational maturity, compliance requirements, and infrastructure goals.

## What Is a PostgreSQL Operator?

A PostgreSQL operator extends the Kubernetes API with custom resources that represent PostgreSQL clusters. Instead of manually managing StatefulSets, PersistentVolumeClaims, ConfigMaps, and backup CronJobs, the operator handles the entire lifecycle:

- **Cluster provisioning** — declarative YAML defines replica count, storage, resource limits
- **Automated failover** — detects primary failure and promotes a replica automatically
- **Backup and restore** — scheduled base backups via pg_basebackup or WAL archiving with continuous point-in-time recovery
- **Connection pooling** — integrates PgBouncer or provides built-in pooler
- **Version upgrades** — rolling major/minor version upgrades with minimal downtime
- **Monitoring** — exports Prometheus metrics for query performance, replication lag, and resource utilization

All three operators covered here are CNCF-aligned, production-grade, and used by hundreds of organizations in production environments.

## Comparison Table

| Feature | CloudNativePG | Zalando Postgres Operator | CrunchyData Postgres Operator |
|---------|---------------|---------------------------|-------------------------------|
| **GitHub Stars** | 8,589 | 5,153 | 4,406 |
| **Language** | Go | Go | Go |
| **License** | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| **CNCF Status** | Sandbox | Graduated project (Eclipse) | Independent (Percona-acquired) |
| **Backup Method** | pg_basebackup + WAL archiving | pgBackRest, WAL-E | pgBackRest |
| **Connection Pooling** | PgBouncer (native) | PgBouncer (native) | PgBouncer (native) |
| **Replication** | Streaming replication | Streaming + logical | Streaming + logical |
| **WAL Archiving** | S3, Azure Blob, GCS | S3, GCS, Azure | S3, GCS, Azure |
| **Major Version Upgrades** | Rolling upgrade | In-place upgrade | Rolling upgrade |
| **Monitoring** | Prometheus metrics + Grafana dashboard | Prometheus exporter | Prometheus exporter |
| **HA Architecture** | Kubernetes-native (leader election) | Patroni-based | Patroni-based |
| **Minikube/Dev Support** | ✅ Full support | ✅ Full support | ✅ Full support |
| **FIPS Compliance** | Configurable | Configurable | ✅ Built-in |

## CloudNativePG

**CloudNativePG** (formerly known as Cloud Native PostgreSQL by EDB) is a Kubernetes-native PostgreSQL operator designed from the ground up for cloud environments. It does not rely on Patroni or external tools — the operator itself implements cluster management logic.

### Key Features

- **Declarative cluster management** — define your entire PostgreSQL cluster in a single `Cluster` resource
- **Online backup** — take base backups without interrupting database operations
- **Automated failover** — uses Kubernetes leader election for primary selection
- **Tablespace management** — native support for PostgreSQL tablespaces on separate volumes
- **Rolling updates** — zero-downtime minor version updates, coordinated major version upgrades
- **Plugin system** — extend with custom plugins for monitoring, security, and backup integrations

### Docker Compose Quick Start

CloudNativePG is designed for Kubernetes, but you can test it locally using `kind` or `minikube`:

```bash
# Install CloudNativePG operator
kubectl apply --server-side -f   https://raw.githubusercontent.com/cloudnative-pg/cloudnative-pg/main/releases/cnpg-1.24.0.yaml

# Create a PostgreSQL cluster
cat <<EOF | kubectl apply -f -
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: my-cluster
spec:
  instances: 3
  storage:
    size: 1Gi
  bootstrap:
    initdb:
      database: appdb
      owner: appuser
EOF

# Connect to the primary
kubectl cnpg psql my-cluster -U appuser -d appdb
```

### When to Choose CloudNativePG

- You want a **purely Kubernetes-native** operator without external dependencies like Patroni
- You need **active-active read scaling** with automatic read/write split
- You prefer **declarative configuration** over imperative cluster management
- Your team is already familiar with Kubernetes resource patterns

## Zalando Postgres Operator

The **Zalando Postgres Operator** is one of the oldest and most battle-tested PostgreSQL operators for Kubernetes, originally developed by Zalando for their e-commerce platform. It uses **Patroni** under the hood for high availability and **pgBackRest** for backup management.

### Key Features

- **Patroni-based HA** — leverages the industry-standard Patroni for leader election and failover
- **Team-based management** — integrates with LDAP/OAuth for multi-team PostgreSQL provisioning
- **Logical replication** — supports logical replication slots for cross-cluster data sync
- **Connection pooling** — built-in PgBouncer with automatic configuration
- **pgBouncer sidecar** — deploys PgBouncer as a sidecar for each instance
- **Spilo image** — uses Zalando's optimized PostgreSQL Docker image (Spilo) with pre-installed extensions

### Docker Compose Quick Start

```bash
# Install the operator via Helm
helm install postgres-operator   postgres-operator/postgres-operator   --namespace postgres-operator --create-namespace

# Deploy a PostgreSQL cluster
cat <<EOF | kubectl apply -f -
apiVersion: "acid.zalan.do/v1"
kind: postgresql
metadata:
  name: acid-minimal-cluster
  namespace: default
spec:
  teamId: "acid"
  volume:
    size: 1Gi
  numberOfInstances: 2
  users:
    appuser:
      - superuser
      - createdb
  databases:
    appdb: appuser
  postgresql:
    version: "16"
EOF
```

### When to Choose Zalando Postgres Operator

- You need **Patroni's proven HA** track record (used by Spotify, Zalando, and others)
- You run **multi-team environments** with team-based database provisioning
- You want **logical replication** for cross-cluster data synchronization
- Your organization already uses **Spilo** (Zalando's PostgreSQL image)

## CrunchyData Postgres Operator

The **CrunchyData Postgres Operator** (PGO) is a production-grade PostgreSQL operator backed by CrunchyData, a company with deep PostgreSQL expertise. It combines Patroni for HA with pgBackRest for enterprise-grade backup and recovery.

### Key Features

- **Full-stack PostgreSQL management** — from provisioning to backup to disaster recovery
- **pgBackRest integration** — enterprise backup with parallel processing, encryption, and retention policies
- **Standalone PgBouncer** — deploys PgBouncer as a separate Deployment for centralized connection management
- **Clone and restore** — clone clusters from existing backups for dev/test environments
- **Standby clusters** — create read-only standby clusters in different Kubernetes clusters or regions
- **Custom extensions** — support for PostGIS, pgvector, timescaledb, and other popular extensions
- **FIPS 140-2 compliance** — meets federal security requirements out of the box

### Docker Compose Quick Start

```bash
# Install PGO via kubectl
kubectl apply -k kustomize/install/namespace
kubectl apply -k kustomize/install/default

# Create a PostgreSQL cluster
cat <<EOF | kubectl apply -f -
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
            storage: 1Gi
  backups:
    pgbackrest:
      repos:
        - name: repo1
          volume:
            volumeClaimSpec:
              accessModes:
                - "ReadWriteOnce"
              resources:
                requests:
                  storage: 1Gi
  proxy:
    pgBouncer:
      replicas: 1
EOF
```

### When to Choose CrunchyData Postgres Operator

- You need **enterprise-grade backup** with pgBackRest's advanced features
- You require **FIPS 140-2 compliance** for regulated industries
- You want **standby clusters** across multiple Kubernetes clusters or regions
- You need **custom PostgreSQL extensions** with pre-built container images
- Your organization values **commercial support** from a PostgreSQL-focused vendor

## Choosing the Right PostgreSQL Operator

| Criteria | CloudNativePG | Zalando | CrunchyData |
|----------|---------------|---------|-------------|
| **Simplest setup** | ✅ | | |
| **Most mature HA** | | ✅ (Patroni) | ✅ (Patroni) |
| **Best backup** | | | ✅ (pgBackRest) |
| **Multi-team support** | | ✅ | |
| **FIPS compliance** | Configurable | Configurable | ✅ |
| **Commercial support** | EDB | Zalando | CrunchyData |
| **Community activity** | High | High | High |

**For greenfield Kubernetes deployments**, CloudNativePG offers the cleanest Kubernetes-native experience with the least operational overhead.

**For organizations already using Patroni**, the Zalando operator provides the smoothest migration path with team-based multi-tenancy.

**For regulated industries** (finance, healthcare, government), CrunchyData's FIPS compliance and enterprise backup capabilities make it the safest choice.

## Why Self-Host Your PostgreSQL Infrastructure?

Managing PostgreSQL on your own infrastructure gives you complete control over data residency, performance tuning, and compliance. When combined with Kubernetes operators, you get the automation benefits of managed services without the vendor lock-in or per-core licensing costs.

Self-hosted PostgreSQL operators eliminate the markup that cloud providers charge for managed database services — often 3-5x the cost of equivalent compute and storage. More importantly, they allow you to:

- **Keep data on-premises** for regulatory compliance (GDPR, HIPAA, PCI-DSS)
- **Tune PostgreSQL parameters** without provider-imposed limits
- **Install custom extensions** that managed services don't support (pgvector, custom FDWs)
- **Scale horizontally** across your own hardware without per-instance fees
- **Avoid vendor lock-in** — your PostgreSQL clusters run on any Kubernetes distribution

For database migration strategies, see our [PostgreSQL Logical Replication guide](../2026-05-10-postgresql-logical-replication-pglogical-wal2json-pgoutput-guide/). For Kubernetes security, check our [container hardening guide](../2026-04-20-kube-bench-vs-trivy-vs-kubescape-container-kubernetes-hardening-guide-2026/). And for backup strategies across all your infrastructure, our [backup verification guide](../2026-04-19-self-hosted-backup-verification-testing-integrity-guide/) covers essential integrity testing practices.

## FAQ

### What is the difference between CloudNativePG and the Zalando Postgres Operator?

CloudNativePG implements cluster management natively within Kubernetes without relying on external tools, while the Zalando operator uses Patroni (a proven HA framework) for leader election and failover. CloudNativePG is better for teams wanting a pure Kubernetes experience; Zalando is better for teams that want Patroni's battle-tested HA.

### Can I migrate between PostgreSQL operators?

Yes, but it requires careful planning. You can use logical replication or pg_dump/pg_restore to migrate data between clusters managed by different operators. Major version upgrades should be planned as separate migration events.

### Do these operators support PostgreSQL extensions like PostGIS and pgvector?

All three operators support custom PostgreSQL extensions. CloudNativePG uses image customization, Zalando uses the Spilo image (which includes many popular extensions), and CrunchyData provides pre-built images with PostGIS, pgvector, and other extensions.

### How does backup work with PostgreSQL operators?

CloudNativePG uses pg_basebackup with WAL archiving to object storage (S3, GCS, Azure). Zalando supports both pgBackRest and WAL-E. CrunchyData uses pgBackRest exclusively, offering the most feature-rich backup with parallel processing, encryption, and retention policies.

### Can I run PostgreSQL operators on OpenShift?

Yes, all three operators support OpenShift. CrunchyData has specific OpenShift certification, CloudNativePG has documented OpenShift deployment procedures, and the Zalando operator runs on any Kubernetes distribution including OpenShift.

### What is the minimum Kubernetes version required?

CloudNativePG requires Kubernetes 1.24+. The Zalando operator requires Kubernetes 1.22+. CrunchyData PGO requires Kubernetes 1.25+. All three support the latest stable Kubernetes releases.

### How many PostgreSQL instances can a single operator manage?

There is no hard limit — the operators are designed to manage hundreds of clusters within a single Kubernetes cluster. The practical limit depends on your Kubernetes cluster's resources and the operator's resource requests/limits configuration.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL Operators: CloudNativePG vs Zalando vs CrunchyData (2026)",
  "description": "Compare the three leading open-source PostgreSQL operators for Kubernetes: CloudNativePG, Zalando Postgres Operator, and CrunchyData PGO. Learn which operator fits your production needs.",
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
