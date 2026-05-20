---
title: "Self-Hosted MySQL Operators: Vitess vs RadonDB vs Presslabs MySQL Operator"
date: "2026-05-20"
tags: ["mysql", "kubernetes", "database-operators", "kubernetes-operators", "database"]
draft: false
---

MySQL remains one of the most widely deployed relational databases, but running it on Kubernetes introduces operational challenges that a standard Deployment cannot solve. Replica set management, automated failover, backup scheduling, schema migrations, and horizontal scaling all require specialized orchestration. MySQL Kubernetes operators encode these operational patterns into declarative custom resources, turning MySQL from a manually managed stateful workload into a cloud-native service.

This guide compares three open-source approaches to running MySQL on Kubernetes: **Vitess** (the industry-standard MySQL sharding system), **RadonDB MySQL Kubernetes** (a high-availability operator based on Percona Server), and the **Presslabs (Bitpoke) MySQL Operator** (a lightweight operator with Orchestrator-based failover).

## MySQL Kubernetes Operators Overview

| Feature | Vitess | RadonDB MySQL | Presslabs MySQL Operator |
|---------|--------|---------------|--------------------------|
| GitHub Stars | ~20,970 | ~370 | ~1,090 |
| License | Apache 2.0 | Apache 2.0 | Apache 2.0 |
| MySQL Flavor | MySQL 8.0, Percona, MariaDB | Percona Server 8.0 | Percona Server 8.0, MySQL |
| Sharding | Yes (horizontal, automatic) | No (HA only) | No (HA only) |
| Proxy Layer | VTGate (SQL proxy) | ProxySQL | Built-in service routing |
| Backup Method | VTBackup (logical) | XtraBackup (physical) | XtraBackup (physical) |
| Point-in-Time Recovery | Yes (binlog-based) | No | Yes (binlog-based) |
| Automated Failover | Yes (via VTTablet) | Yes (via MySQL MGR or Xenon) | Yes (via Orchestrator) |
| Connection Pooling | Built-in (VTGate) | Via ProxySQL sidecar | No (direct connection) |
| Multi-Region | Yes | Yes | No |
| Operator Pattern | Custom (vtctl, vtgate) | Standard Kubernetes operator | Standard Kubernetes operator |
| Dashboard | Vitess Dashboard | RadonDB Dashboard | No built-in dashboard |

## Vitess

Vitess is a database clustering system for horizontal scaling of MySQL, originally developed by YouTube to handle their massive database workload. It is now a CNCF graduated project and the most mature MySQL scaling solution for Kubernetes.

### Architecture

Vitess introduces several components beyond standard MySQL:

- **VTGate**: A stateless SQL proxy that routes queries to the correct shard
- **VTTablet**: A sidecar process running alongside each MySQL instance that handles health checks, backups, and query serving
- **VTCTLD**: The control plane for topology management and schema changes
- **VTOrc**: Automated recovery controller for tablet failover

### Deployment with Helm

```yaml
# values.yaml for vitess
global:
  image:
    repository: vitess/vtserver
    tag: v21.0.0

cells:
  - name: cell1
    mysqlProtocol:
      authType: static
      username: vtadmin
      password: vtadmin

etcd:
  replicas: 3

vtctld:
  replicas: 1

vtgate:
  replicas: 2
  resources:
    requests:
      cpu: 500m
      memory: 512Mi

vttablet:
  replicas: 2
  resources:
    requests:
      cpu: 1
      memory: 2Gi
  volumeSize: 50Gi
```

```bash
# Deploy Vitess
helm install vitess vitess/vitess -f values.yaml --namespace vitess

# Connect via VTGate
mysql -h <vtgate-service> -P 15306 -u vtadmin -pvtadmin
```

### Sharding Configuration

```yaml
apiVersion: planetscale.com/v2
kind: VitessCluster
metadata:
  name: example
spec:
  cells:
    - name: cell1
      mysqlProtocol:
        authType: static
  keyspaces:
    - name: commerce
      shards:
        - name: "-"
          tabletPools:
            - cell: cell1
              type: replica
              replicas: 2
              vttablet:
                resources:
                  requests:
                    cpu: 500m
                    memory: 1Gi
              dataVolumeClaimTemplate:
                accessModes: ["ReadWriteOnce"]
                resources:
                  requests:
                    storage: 20Gi
```

### Key Strengths

Vitess is the only option in this comparison that provides **true horizontal scaling through sharding**. It transparently splits tables across multiple MySQL instances, routes queries to the correct shard via VTGate, and supports online schema changes (VReplication) that do not block writes.

The built-in **connection pooling** in VTGate eliminates the need for a separate connection pooler like ProxySQL or PgBouncer. Each VTGate instance maintains persistent connections to backend tablets and multiplexes client connections, dramatically reducing MySQL connection overhead.

## RadonDB MySQL Kubernetes

RadonDB MySQL is a high-availability MySQL operator built on Percona Server for MySQL, using MySQL Group Replication (MGR) or the Xenon high-availability component for automatic failover.

### Deployment

```yaml
apiVersion: mysql.radondb.com/v1alpha1
kind: MysqlCluster
metadata:
  name: mysql-cluster
spec:
  replicas: 3
  mysqlVersion: "8.0.36"
  image: radondb/radondb-mysql-kubernetes:8.0.36
  resources:
    requests:
      cpu: 500m
      memory: 1Gi
    limits:
      cpu: "2"
      memory: 4Gi
  storageType: Persistent
  dataVolumeClaimSpec:
    accessModes:
      - ReadWriteOnce
    resources:
      requests:
        storage: 20Gi
  backupSchedule: "0 2 * * *"
  backupHistoryLimit: 7
  backupRemoteRepo:
    endpoint: s3.amazonaws.com
    region: us-east-1
    bucket: mysql-backups
    credentialsSecret: s3-credentials
```

### High Availability with MGR

RadonDB uses MySQL Group Replication for synchronous multi-primary replication:

```yaml
spec:
  options:
    leaderElect:
      enabled: true
    mysqlConf:
      transaction_write_set_extraction: "XXHASH64"
      loose_group_replication:
        group_name: "auto"
        start_on_boot: "ON"
        single_primary_mode: "ON"
```

MGR ensures that all nodes in the cluster agree on transaction ordering, providing strong consistency. If the primary node fails, a new primary is elected automatically within seconds.

### Backup with XtraBackup

RadonDB uses Percona XtraBackup for hot physical backups, which are faster and less resource-intensive than logical dumps for large databases:

```bash
# Operator handles backup automatically per schedule
# To trigger a manual backup:
kubectl apply -f - <<EOF
apiVersion: mysql.radondb.com/v1alpha1
kind: MysqlBackup
metadata:
  name: manual-backup
spec:
  clusterName: mysql-cluster
EOF
```

## Presslabs (Bitpoke) MySQL Operator

The Presslabs MySQL Operator (now maintained by Bitpoke) takes a lightweight approach, focusing on automated failover via Orchestrator and XtraBackup-based backups.

### Deployment

```yaml
apiVersion: mysql.presslabs.org/v1alpha1
kind: MysqlCluster
metadata:
  name: my-cluster
spec:
  replicas: 3
  secretName: my-cluster-secret
  mysqlVersion: "8.0"
  image: percona/percona-server:8.0
  minBackupReplicas: 1
  backupSchedule: "0 2 * * *"
  backupURL: "s3://mysql-backups/my-cluster"
  backupSecretName: s3-credentials
```

### Orchestrator-Based Failover

The operator deploys GitHub's Orchestrator alongside the MySQL cluster to detect failures and promote new primaries:

```yaml
apiVersion: mysql.presslabs.org/v1alpha1
kind: MysqlCluster
metadata:
  name: my-cluster
spec:
  orchestrator:
    enabled: true
    image: openark/orchestrator:latest
    topologyRecover: true
    raftBind: "0.0.0.0:10008"
```

Orchestrator continuously monitors the replication topology and performs automatic failover when it detects a primary failure. It also provides a web UI for visualizing the replication topology and performing manual failovers.

### Database Initialization

```yaml
apiVersion: mysql.presslabs.org/v1alpha1
kind: Database
metadata:
  name: mydb
spec:
  clusterRef:
    name: my-cluster
  characterSet: utf8mb4
  collation: utf8mb4_unicode_ci
---
apiVersion: mysql.presslabs.org/v1alpha1
kind: MysqlUser
metadata:
  name: myapp-user
spec:
  clusterRef:
    name: my-cluster
  allowedHosts:
    - "%"
  resourceRequirements:
    queriesPerHour: 1000
    updatesPerHour: 500
```

The operator manages databases and users as first-class Kubernetes resources, creating them automatically on the MySQL cluster.

## Why Self-Host MySQL on Kubernetes?

MySQL is available as a managed service from every cloud provider (RDS, Cloud SQL, Azure Database). Yet many teams choose to self-host on Kubernetes for specific operational and business reasons.

**Cost predictability**: Managed MySQL pricing includes markups on compute, storage, and IOPS that compound quickly. A managed MySQL instance with 4 vCPUs, 16 GB RAM, and 500 GB SSD costs approximately $600-$900/month on major cloud providers. Running the same configuration on your own Kubernetes cluster with local SSD or network storage typically costs $150-$300/month in raw infrastructure. For teams running 10+ MySQL instances, the savings justify the operational overhead.

**Schema migration control**: Managed services restrict long-running DDL operations, enforce maintenance windows, and limit schema change throughput. With self-hosted MySQL on Kubernetes, you control the migration strategy — whether that is online schema changes via gh-ost, VReplication through Vitess, or standard ALTER TABLE during off-peak hours.

**Custom MySQL configuration**: Self-hosting gives you full access to `my.cnf` tuning parameters: innodb_buffer_pool_size, innodb_log_file_size, max_connections, query_cache settings, and replication configuration. Managed services restrict many of these to prevent misconfiguration, but performance-critical workloads often need fine-grained tuning.

**Multi-region replication control**: When you manage the replication topology yourself, you decide which regions get synchronous replicas, which get asynchronous read replicas, and how failover priority is configured. Managed services enforce their own replication patterns, which may not match your latency and durability requirements.

For teams also managing other database types, our [MongoDB operators comparison](../2026-05-20-self-hosted-mongodb-operators-mongodb-community-percona-kubeblocks-guide/) covers the NoSQL side, and our [PostgreSQL HA guide](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/) covers PostgreSQL failover patterns. If you need MySQL backup strategies without an operator, our [MySQL backup comparison](../percona-xtrabackup-vs-mydumper-vs-mariabackup-self-hosted-mysql-backup-guide/) covers the tools directly. For connection pooling needs, our [database connection pooler comparison](../pgbouncer-vs-proxysql-vs-odyssey-self-hosted-database-connection-pooling-guide/) covers ProxySQL, which integrates with all three operators in this article.

## Choosing the Right MySQL Operator

**Choose Vitess if:** you need horizontal scaling through sharding, connection pooling, and enterprise-grade MySQL orchestration. It is the choice for high-traffic applications that have outgrown single-instance MySQL. The learning curve is steep, but the scalability ceiling is essentially unlimited.

**Choose RadonDB MySQL if:** you need a straightforward high-availability MySQL operator with MGR-based replication, XtraBackup integration, and a simple declarative API. It is ideal for teams that need HA MySQL on Kubernetes without the complexity of sharding.

**Choose Presslabs MySQL Operator if:** you prefer Orchestrator-based failover with a lightweight operator footprint and database/user CRDs. It is a good fit for teams that want MySQL HA with minimal operator overhead and appreciate the visual replication topology that Orchestrator provides.

## FAQ

### Can Vitess run without sharding?

Yes. Vitess can manage a single unsharded keyspace (the `-` shard). In this mode, you get VTGate connection pooling, VTTablet health management, automated backups, and VTOrc failover — all the operational benefits without sharding complexity. Many teams start with an unsharded Vitess deployment and add shards later when needed.

### Does RadonDB support MySQL 5.7?

RadonDB MySQL Kubernetes primarily targets MySQL 8.0 (Percona Server). MySQL 5.7 support is available in older operator versions but is not recommended for new deployments, as MySQL 5.7 reached end-of-life in October 2023.

### How does Vitess handle schema migrations?

Vitess uses VReplication for online schema changes. The `vtctl ApplySchema` command creates a shadow table with the new schema, copies data from the original table using binary log replay, and then atomically swaps the tables. This process does not block reads or writes and works on tables with billions of rows.

### Can I migrate from a standalone MySQL instance to a Kubernetes operator?

Yes, but the process varies by operator. For Vitess, use `vtctl Backup` to create a backup from the source, then restore into the Vitess cluster. For RadonDB and Presslabs, use XtraBackup to create a physical backup, copy it to the operator's backup storage, and trigger a restore. Plan for a maintenance window during the cutover.

### What happens when the primary MySQL node fails?

All three operators handle automatic failover, but through different mechanisms. Vitess uses VTOrc to detect tablet failures and promote a new primary. RadonDB uses MySQL Group Replication consensus for automatic primary election. The Presslabs Operator uses Orchestrator to detect replication lag and promote the most up-to-date replica. Failover typically completes within 10-30 seconds.

### Does the Presslabs Operator support GTID-based replication?

Yes. The operator configures GTID-based replication by default, which simplifies failover (any replica can become primary without binlog position calculations) and enables parallel replication for improved throughput.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MySQL Operators: Vitess vs RadonDB vs Presslabs MySQL Operator",
  "description": "Compare three open-source Kubernetes operators for running MySQL in production: Vitess, RadonDB MySQL, and Presslabs MySQL Operator. Covers sharding, HA, backups, and failover.",
  "datePublished": "2026-05-20",
  "dateModified": "2026-05-20",
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
