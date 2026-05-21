---
title: "Self-Hosted PostgreSQL High Availability on Kubernetes: Stolon vs Spilo vs Patroni (2026)"
date: "2026-05-21"
tags: ["postgresql", "high-availability", "kubernetes", "kubernetes-operator", "database", "self-hosted", "devops"]
draft: false
---

Running PostgreSQL in production demands high availability, automatic failover, and seamless recovery from node failures. On Kubernetes, these requirements are amplified — pods restart, nodes go down, and storage volumes need to follow the primary instance. This guide compares three proven solutions for self-hosted PostgreSQL HA on Kubernetes: **Stolon**, **Spilo**, and **Patroni**.

## The PostgreSQL High Availability Challenge

PostgreSQL's built-in streaming replication provides data redundancy but doesn't handle automatic failover. When the primary node fails, someone (or something) needs to promote a standby to primary, update connection endpoints, and ensure no split-brain scenarios occur. On bare metal, tools like repmgr or Pacemaker handle this. On Kubernetes, the challenge is more complex: pods are ephemeral, persistent volumes must be managed, and the Kubernetes control plane needs to understand PostgreSQL's HA topology.

For a broader comparison of PostgreSQL HA strategies across all infrastructure types, see our [Patroni vs Galera vs repmgr guide](../patroni-vs-galera-cluster-vs-repmgr-self-hosted-database-high-availability-guide-2026/). For PostgreSQL logical replication patterns, check our [pgLogical vs wal2json vs pgOutput comparison](../2026-05-10-postgresql-logical-replication-pglogical-wal2json-pgoutput-guide/). For PostgreSQL backup strategies, our [pgBackRest vs Barman vs WAL-G guide](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/) covers disaster recovery.

## Patroni

[Patroni](https://github.com/patroni/patroni) by Zalando is the most widely adopted PostgreSQL HA framework. It uses a distributed consensus store (etcd, Consul, ZooKeeper, or Kubernetes) for leader election and manages PostgreSQL streaming replication with automatic failover.

**Key Features:**
- **Pluggable DCS** — supports etcd, Consul, ZooKeeper, Kubernetes (native)
- **Automatic failover** — detects primary failure and promotes a standby within seconds
- **Connection pooling integration** — works with PgBouncer, Pgpool-II, and Odyssey
- **Kubernetes native mode** — uses Kubernetes endpoints and configmaps instead of external DCS
- **REST API** — programmatic control and monitoring
- **Switchover support** — planned primary transitions with minimal downtime
- **WAL archiving** — integrates with WAL-E, WAL-G, and pgBackRest

**Kubernetes deployment with Patroni:**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: patroni-config
data:
  patroni.yaml: |
    scope: postgres-cluster
    name: patroni-node-1
    restapi:
      listen: 0.0.0.0:8008
    kubernetes:
      namespace: default
      labels:
        cluster: postgres-ha
    postgresql:
      listen: 0.0.0.0:5432
      data_dir: /var/lib/postgresql/data
      parameters:
        max_connections: 200
        shared_buffers: 256MB
      pg_hba:
        - host all all 0.0.0.0/0 md5
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: patroni-postgres
spec:
  serviceName: patroni
  replicas: 3
  selector:
    matchLabels:
      app: patroni-postgres
  template:
    metadata:
      labels:
        app: patroni-postgres
    spec:
      containers:
        - name: patroni
          image: ghcr.io/zalando/patroni:latest
          ports:
            - containerPort: 5432
            - containerPort: 8008
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
            - name: patroni-config
              mountPath: /etc/patroni
      volumes:
        - name: patroni-config
          configMap:
            name: patroni-config
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 50Gi
```

Patroni's Kubernetes mode eliminates the need for a separate etcd cluster — it uses Kubernetes endpoints for leader election, simplifying the architecture significantly.

## Spilo

[Spilo](https://github.com/zalando/spilo) is Zalando's PostgreSQL Docker image that bundles Patroni, pgBouncer, and a collection of useful PostgreSQL extensions into a single, production-ready container. Spilo is the runtime that powers the Zalando Postgres Operator.

**Key Features:**
- **Patroni built-in** — HA and failover handled by Patroni out of the box
- **Extension-rich** — pre-installed extensions include PostGIS, pgvector, timescaledb, pgaudit
- **pgBouncer included** — connection pooling without separate deployment
- **Optimized configuration** — tuned PostgreSQL settings for container environments
- **WAL-E integration** — automatic WAL archiving to S3-compatible storage
- **Multiple PostgreSQL versions** — supports PG 13 through PG 17

**Spilo Docker image:**
```bash
docker run -d \
  --name spilo-postgres \
  -e SPILO_CONFIGURATION='{"kubernetes": {"namespace": "default"}}' \
  -e PGUSER_ADMIN=admin \
  -e PGPASSWORD_ADMIN=secretpass \
  -e SCOPE=postgres-cluster \
  -e PGVERSION=16 \
  registry.opensource.zalan.do/acid/spilo-16:latest
```

**Spilo + Postgres Operator (Zalando operator):**
```yaml
apiVersion: "acid.zalan.do/v1"
kind: postgresql
metadata:
  name: acid-minimal-cluster
spec:
  teamId: "acid"
  volume:
    size: 10Gi
  numberOfInstances: 3
  users:
    app_user:
      - superuser
      - createdb
  databases:
    appdb: app_user
  postgresql:
    version: "16"
  connectionPooler:
    numberOfInstances: 2
    mode: "session"
    schema: "pooler"
    user: "pooler"
```

Spilo is not a standalone HA tool — it's the container image that makes Patroni production-ready in Kubernetes. If you're using the Zalando Postgres Operator, you're already using Spilo under the hood.

## Stolon

[Stolon](https://github.com/sorintlab/stolon) is a PostgreSQL HA manager designed specifically for cloud-native environments. Unlike Patroni, which can run anywhere with a DCS, Stolon is purpose-built for Kubernetes and cloud platforms with a proxy-based architecture.

**Key Features:**
- **Proxy architecture** — a dedicated proxy layer routes traffic to the current primary
- **Kubernetes native** — designed from the ground up for container orchestration
- **Consul/etcd/Kubernetes DCS** — flexible distributed consensus store options
- **Automatic primary election** — uses the keeper/keeper-proxy/sentinel architecture
- **No split-brain** — strict fencing ensures only one primary exists
- **Configurable failover parameters** — tune failover detection timing

**Stolon Docker Compose deployment:**
```yaml
version: "3.8"
services:
  consul:
    image: consul:1.17
    command: agent -dev -client=0.0.0.0

  stolon-keeper-1:
    image: sorintlab/stolon:latest
    command: >
      stolon-keeper
      --cluster-name=pg-cluster
      --store-backend=consul
      --store-endpoints=consul:8500
      --pg-listen-address=0.0.0.0
      --pg-data-path=/var/lib/postgresql/data
    environment:
      - PGUSER_SUPERUSER=postgres
      - PGPASSWORD_SUPERUSER=postgres
    volumes:
      - keeper1_data:/var/lib/postgresql/data

  stolon-keeper-2:
    image: sorintlab/stolon:latest
    command: >
      stolon-keeper
      --cluster-name=pg-cluster
      --store-backend=consul
      --store-endpoints=consul:8500
      --pg-listen-address=0.0.0.0
      --pg-data-path=/var/lib/postgresql/data
    environment:
      - PGUSER_SUPERUSER=postgres
      - PGPASSWORD_SUPERUSER=postgres
    volumes:
      - keeper2_data:/var/lib/postgresql/data

  stolon-sentinel:
    image: sorintlab/stolon:latest
    command: >
      stolon-sentinel
      --cluster-name=pg-cluster
      --store-backend=consul
      --store-endpoints=consul:8500

  stolon-proxy:
    image: sorintlab/stolon:latest
    command: >
      stolon-proxy
      --cluster-name=pg-cluster
      --store-backend=consul
      --store-endpoints=consul:8500
      --listen-address=0.0.0.0
      --port=5432
    ports:
      - "5432:5432"

volumes:
  keeper1_data:
  keeper2_data:
```

Stolon's architecture separates concerns: keepers manage PostgreSQL instances, sentinals monitor health and trigger elections, and the proxy provides a stable connection endpoint that automatically routes to the current primary.

## Comparison Table

| Feature | Patroni | Spilo | Stolon |
|---------|---------|-------|--------|
| **License** | MIT | MIT | Apache 2.0 |
| **Primary Role** | HA framework | Container image + operator integration | HA manager with proxy |
| **DCS Options** | etcd, Consul, ZooKeeper, Kubernetes | Kubernetes (via operator) | Consul, etcd, Kubernetes |
| **Architecture** | Sidecar-style | Docker image (Patroni + extensions + pgBouncer) | Keeper/Sentinel/Proxy |
| **Kubernetes Native** | Yes (native mode) | Yes (via Postgres Operator) | Yes (purpose-built) |
| **Connection Pooling** | External (PgBouncer, Pgpool-II) | pgBouncer included | External |
| **Extensions** | Manual installation | Pre-installed (PostGIS, pgvector, etc.) | Manual installation |
| **Split-Brain Prevention** | Leader election via DCS | Patroni-based | Strict proxy fencing |
| **GitHub Stars** | 8,400+ | 1,800+ | 4,800+ |
| **Last Active** | May 2026 | May 2026 | July 2024 |
| **Best For** | General PostgreSQL HA everywhere | Kubernetes with operator management | Kubernetes-only with proxy routing |

## Choosing the Right Solution

**Choose Patroni if:**
- You need the most battle-tested PostgreSQL HA framework
- You want flexibility to run on bare metal, VMs, or Kubernetes
- You need integration with external DCS (etcd, Consul, ZooKeeper)
- You want a large community and extensive documentation

**Choose Spilo if:**
- You're already using (or planning to use) the Zalando Postgres Operator
- You want a pre-configured PostgreSQL image with popular extensions
- You need pgBouncer bundled with your PostgreSQL deployment
- You want S3-based WAL archiving out of the box

**Choose Stolon if:**
- You want a proxy-based architecture with automatic connection routing
- You need strict split-brain prevention with fencing
- You're deploying exclusively on Kubernetes
- You prefer a clean separation of concerns (keeper/sentinel/proxy)

## Why Self-Host PostgreSQL HA on Kubernetes?

Running PostgreSQL with high availability on Kubernetes combines the resilience of PostgreSQL streaming replication with Kubernetes' orchestration capabilities:

**Automated failover and recovery:** When a PostgreSQL primary pod fails, the HA manager detects the failure within seconds, promotes a standby to primary, and updates the service endpoint. Applications reconnect automatically without manual intervention.

**Resource efficiency:** Kubernetes schedules PostgreSQL pods alongside other workloads, optimizing resource utilization across the cluster. You don't need dedicated hardware for database HA — PostgreSQL shares the same infrastructure as your application pods.

**Declarative configuration:** Both Patroni and Spilo support declarative configuration through Kubernetes manifests. Define your desired HA topology in YAML, apply it, and the system converges to that state. This enables GitOps workflows where database configuration lives in version control.

**Scaling read replicas:** Kubernetes StatefulSets make it easy to add read replicas by increasing the replica count. The HA manager automatically configures streaming replication from the primary to new standbys, distributing read load across multiple instances.

For PostgreSQL backup and disaster recovery, see our [pgBackRest vs Barman vs WAL-G comparison](../pgbackrest-vs-barman-vs-wal-g-self-hosted-postgresql-backup-guide-2026/). For database query optimization strategies, check our [database tuning guide](../2026-05-03-self-hosted-database-tuning-mysqltuner-pgtune-pgtune-ng-guide/).

## FAQ

### What is the difference between Patroni, Spilo, and Stolon?
Patroni is a PostgreSQL HA framework that handles leader election, automatic failover, and replication management. Spilo is a Docker image that bundles Patroni with pgBouncer and PostgreSQL extensions — it's essentially "Patroni plus extras." Stolon is a separate PostgreSQL HA manager with a proxy-based architecture designed specifically for cloud environments.

### Can Patroni run without etcd?
Yes. Patroni supports multiple distributed consensus stores: etcd, Consul, ZooKeeper, and Kubernetes native mode. In Kubernetes mode, Patroni uses Kubernetes endpoints and configmaps for leader election, eliminating the need for an external DCS cluster.

### Does Spilo work without the Zalando Postgres Operator?
Yes, Spilo can run as a standalone Docker image with Patroni managing HA. However, the Zalando Postgres Operator provides additional automation — automatic backup scheduling, connection pooling, user management, and database provisioning — that makes Spilo significantly easier to manage at scale.

### How does Stolon prevent split-brain scenarios?
Stolon uses a strict fencing mechanism. When the sentinel detects a primary failure, it first updates the cluster state in the DCS. The proxy then stops routing traffic to the old primary. Only after the old primary is confirmed fenced does Stolon promote a new keeper to primary. This ensures only one primary can accept writes at any time.

### Which solution handles the most PostgreSQL connections?
Spilo includes pgBouncer by default, providing connection pooling out of the box. Patroni works well with external PgBouncer deployments. Stolon requires you to deploy a separate connection pooler. For high-connection workloads (10,000+ connections), Spilo's bundled pgBouncer or Patroni + PgBouncer combination is the best choice.

### How do I migrate from a standalone PostgreSQL to any of these HA solutions?
All three solutions support initializing from an existing PostgreSQL data directory. For Patroni, use `patroni --initialize`. For Spilo, configure the `SPILO_CONFIGURATION` with your existing data volume. For Stolon, use `stolonctl init` with the existing keeper data path. Always take a full backup before migrating.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted PostgreSQL High Availability on Kubernetes: Stolon vs Spilo vs Patroni (2026)",
  "description": "Compare three proven PostgreSQL HA solutions for Kubernetes — Patroni, Spilo, and Stolon — covering automatic failover, replication management, and production deployment patterns.",
  "datePublished": "2026-05-21",
  "dateModified": "2026-05-21",
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
