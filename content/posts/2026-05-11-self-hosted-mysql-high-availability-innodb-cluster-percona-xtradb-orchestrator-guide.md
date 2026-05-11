---
title: "Self-Hosted MySQL High Availability: InnoDB Cluster vs Percona XtraDB Cluster vs Orchestrator (2026)"
date: "2026-05-11"
tags: ["mysql", "high-availability", "database", "percona", "clustering", "failover"]
draft: false
---

MySQL remains the world's most popular open-source relational database, but running it in production without a high availability (HA) strategy is a recipe for downtime and data loss. Whether you're managing an e-commerce platform, a SaaS application, or an internal tool, ensuring your MySQL database stays online through hardware failures, network partitions, and planned maintenance is non-negotiable.

This guide compares three leading approaches to MySQL high availability: **MySQL InnoDB Cluster** (Oracle's integrated HA solution), **Percona XtraDB Cluster** (Galera-based synchronous replication), and **MySQL Orchestrator** (asynchronous replication topology management). Each takes a fundamentally different approach to keeping your database online, and the right choice depends on your consistency requirements, operational expertise, and infrastructure constraints.

## What Is MySQL High Availability?

MySQL high availability refers to the set of technologies and practices that ensure a MySQL database remains accessible and operational despite failures. The core challenge is balancing three competing goals: **data consistency** (all nodes agree on the same data), **availability** (the database stays online), and **partition tolerance** (the system survives network splits) — the CAP theorem triangle.

Traditional MySQL replication (asynchronous master-slave) provides basic redundancy but leaves a gap during failover: the primary node must be manually promoted, and any unreplicated transactions are lost. Modern HA solutions address this with automated failover, synchronous replication, or a combination of both.

Key HA metrics include:
- **RPO (Recovery Point Objective)**: How much data can you afford to lose? Synchronous solutions offer zero data loss; asynchronous solutions may lose seconds of transactions.
- **RTO (Recovery Time Objective)**: How quickly can you recover? Automated failover achieves RTOs under 30 seconds; manual promotion can take minutes or hours.
- **Split-brain prevention**: Ensuring two nodes don't both believe they're the primary during a network partition.

## MySQL InnoDB Cluster

MySQL InnoDB Cluster is Oracle's official high availability solution, bundling MySQL Server with Group Replication, MySQL Shell, and MySQL Router into a cohesive package. It uses synchronous multi-primary replication via the Paxos consensus protocol, ensuring all nodes agree on transaction order before committing.

**Key features:**
- Synchronous replication with automatic conflict detection and resolution
- Built-in split-brain protection through quorum-based voting
- MySQL Router provides automatic failover routing for application connections
- MySQL Shell offers adminAPI for cluster management (JavaScript/Python)
- Supports single-primary and multi-primary modes

**Architecture:** InnoDB Cluster requires a minimum of 3 nodes (odd number for quorum). Each node runs MySQL Server with the Group Replication plugin. MySQL Shell manages the cluster lifecycle, and MySQL Router sits between applications and the cluster, directing reads/writes to the appropriate node.

**Best for:** Organizations already invested in the Oracle MySQL ecosystem who want an integrated, supported HA solution with strong consistency guarantees. The single-primary mode is simplest to operate; multi-primary mode offers write scalability but requires careful application design to avoid write conflicts.

## Percona XtraDB Cluster (PXC)

Percona XtraDB Cluster is Percona's Galera-based synchronous replication solution for MySQL and Percona Server. Unlike InnoDB Cluster's Paxos-based approach, PXC uses Galera's virtual synchrony protocol, which provides true synchronous replication with certification-based conflict detection.

**Key features:**
- Synchronous multi-master replication — writes can go to any node
- Automatic node provisioning (SST: State Snapshot Transfer) for joining nodes
- Parallel applying of replicated transactions for better performance
- Built-in flow control to prevent slow nodes from falling behind
- Percona XtraBackup integration for non-blocking SST
- No single point of failure — all nodes are equal masters

**Architecture:** PXC requires a minimum of 3 nodes. Each node runs Percona Server with the Galera wsrep plugin. Writes to any node are replicated synchronously to all others before being committed. The cluster uses a certification-based approach: transactions are applied locally, then certified against other nodes before final commit.

**Best for:** Teams that need true multi-master write capability, geographic distribution with read scalability, or are already using Percona Server for its performance optimizations. PXC is also the go-to choice for workloads that can tolerate the occasional deadlock that Galera's certification may produce under high write contention.

## MySQL Orchestrator

MySQL Orchestrator (github.com/openark/orchestrator) takes a fundamentally different approach: instead of providing its own replication engine, it manages existing MySQL replication topologies. It works with standard asynchronous or semi-synchronous MySQL replication, providing automated failover, topology visualization, and recovery orchestration.

**Key features:**
- Works with any MySQL replication setup (async, semi-sync, GTID-based)
- Automatic crash detection and failover with configurable promotion rules
- Web-based topology visualization and manual intervention interface
- Pseudo-GTID support for topology refactoring without GTIDs
- Hooks and API integration for custom recovery workflows
- Supports complex topologies: master-slave, chained replication, fan-out

**Architecture:** Orchestrator runs as a separate service that continuously monitors your MySQL replication topology via the MySQL API. It discovers the topology, tracks health, and when a failure is detected, executes a configurable recovery plan. Unlike InnoDB Cluster and PXC, Orchestrator doesn't change how MySQL replicates data — it manages the existing replication infrastructure.

**Best for:** Organizations with established MySQL replication setups that want automated failover without changing their replication architecture. Also ideal for teams managing complex, multi-tier replication topologies (e.g., primary → secondary → analytics replica) where integrated solutions like InnoDB Cluster don't fit.

## Comparison: InnoDB Cluster vs Percona XtraDB Cluster vs Orchestrator

| Feature | MySQL InnoDB Cluster | Percona XtraDB Cluster | MySQL Orchestrator |
|---------|---------------------|----------------------|-------------------|
| **Replication Type** | Synchronous (Group Replication) | Synchronous (Galera) | Manages async/semi-sync |
| **Write Model** | Single or multi-primary | Multi-master | Single primary |
| **Minimum Nodes** | 3 | 3 | 2 (1 primary + 1 replica) |
| **Failover** | Automatic (built-in) | Automatic (built-in) | Automatic (orchestrated) |
| **Consistency** | Strong (Paxos) | Strong (Galera cert) | Eventual (async replication) |
| **RPO** | Zero data loss | Zero data loss | Potential data loss (async) |
| **RTO** | < 30 seconds | < 30 seconds | < 60 seconds |
| **Split-Brain Protection** | Quorum-based | Galera PC mechanism | Orchestrator detection |
| **Write Scalability** | Limited (single-primary) | Excellent (multi-master) | Limited (single primary) |
| **Operational Complexity** | Moderate | Moderate-High | Low-Moderate |
| **Vendor Lock-in** | Oracle MySQL | Percona Server | None (works with any MySQL) |
| **GitHub Stars** | 12,264 (mysql-server) | 381 (PXC) | 5,762 (orchestrator) |
| **Docker Support** | Official images | Percona images | Community images |

## Docker Compose Deployments

### MySQL InnoDB Cluster

MySQL InnoDB Cluster can be deployed using Oracle's official Docker images. Here's a minimal 3-node setup:

```yaml
version: "3.8"
services:
  mysql1:
    image: mysql:8.4
    container_name: mysql-innodb-1
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      MYSQL_ROOT_HOST: "%"
    ports:
      - "3306:3306"
    command: >
      --server-id=1
      --gtid-mode=ON
      --enforce-gtid-consistency=ON
      --binlog-checksum=NONE
      --loose-group-replication-group-name="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
      --loose-group-replication-local-address="mysql1:33061"
      --loose-group-replication-group-seeds="mysql1:33061,mysql2:33061,mysql3:33061"
    networks:
      cluster-net:
        aliases: [mysql1]

  mysql2:
    image: mysql:8.4
    container_name: mysql-innodb-2
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
    command: >
      --server-id=2
      --gtid-mode=ON
      --enforce-gtid-consistency=ON
      --binlog-checksum=NONE
      --loose-group-replication-group-name="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
      --loose-group-replication-local-address="mysql2:33061"
      --loose-group-replication-group-seeds="mysql1:33061,mysql2:33061,mysql3:33061"
      --loose-group-replication-start-on-boot=OFF
    depends_on: [mysql1]
    networks: [cluster-net]

  mysql3:
    image: mysql:8.4
    container_name: mysql-innodb-3
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
    command: >
      --server-id=3
      --gtid-mode=ON
      --enforce-gtid-consistency=ON
      --binlog-checksum=NONE
      --loose-group-replication-group-name="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
      --loose-group-replication-local-address="mysql3:33061"
      --loose-group-replication-group-seeds="mysql1:33061,mysql2:33061,mysql3:33061"
      --loose-group-replication-start-on-boot=OFF
    depends_on: [mysql1]
    networks: [cluster-net]

  mysqlrouter:
    image: mysql/mysql-router:8.4
    environment:
      MYSQL_ROUTER_USERNAME: router
      MYSQL_ROUTER_PASSWORD: routerpass
      MYSQL_HOST: mysql1
      MYSQL_PORT: 3306
    ports:
      - "6446:6446"
      - "6447:6447"
    depends_on: [mysql1, mysql2, mysql3]
    networks: [cluster-net]

networks:
  cluster-net:
    driver: bridge
```

### Percona XtraDB Cluster

```yaml
version: "3.8"
services:
  pxc1:
    image: percona/percona-xtradb-cluster:8.0
    container_name: pxc-node-1
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      CLUSTER_NAME: pxc-cluster
      CLUSTER_JOIN: ""
    ports:
      - "3306:3306"
      - "4444:4444"
      - "4567:4567"
      - "4568:4568"
    volumes:
      - pxc1-data:/var/lib/mysql
    networks:
      pxc-net:
        aliases: [pxc1]

  pxc2:
    image: percona/percona-xtradb-cluster:8.0
    container_name: pxc-node-2
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      CLUSTER_NAME: pxc-cluster
      CLUSTER_JOIN: pxc1
    ports:
      - "3307:3306"
    volumes:
      - pxc2-data:/var/lib/mysql
    depends_on: [pxc1]
    networks: [pxc-net]

  pxc3:
    image: percona/percona-xtradb-cluster:8.0
    container_name: pxc-node-3
    environment:
      MYSQL_ROOT_PASSWORD: rootpass
      CLUSTER_NAME: pxc-cluster
      CLUSTER_JOIN: pxc1
    ports:
      - "3308:3306"
    volumes:
      - pxc3-data:/var/lib/mysql
    depends_on: [pxc1]
    networks: [pxc-net]

volumes:
  pxc1-data:
  pxc2-data:
  pxc3-data:

networks:
  pxc-net:
    driver: bridge
```

### MySQL Orchestrator

```yaml
version: "3.8"
services:
  orchestrator:
    image: openarkcode/orchestrator:latest
    container_name: mysql-orchestrator
    ports:
      - "3000:3000"
    environment:
      ORC_TOPOLOGY_USER: orchestrator
      ORC_TOPOLOGY_PASSWORD: orchestrator_pass
      ORC_BACKEND_DB_TYPE: sqlite
    volumes:
      - ./orchestrator.conf.json:/etc/orchestrator.conf.json
    networks: [orch-net]

  # Your existing MySQL primary and replicas go here
  # Orchestrator discovers and manages them automatically

networks:
  orch-net:
    driver: bridge
```

The orchestrator configuration file (`orchestrator.conf.json`) specifies which MySQL instances to monitor and the recovery policies to apply:

```json
{
  "Debug": true,
  "BackendDB": "sqlite",
  "DiscoverByShowSlaveHosts": true,
  "InstancePollSeconds": 5,
  "DiscoveryIgnoreReplicaHostnameFilters": [],
  "UnseenInstanceForgetHours": 240,
  "SnapshotTopologiesIntervalHours": 0,
  "InstanceBulkOperations": 20,
  "HostnameResolveMethod": "default",
  "MySQLHostnameResolveMethod": "@@hostname",
  "SkipBinlogServerUnresolveCheck": true,
  "ExpiryHostnameResolvesMinutes": 60,
  "RejectZipMatch": false,
  "VerifyReplicationFilters": false,
  "ReasonableReplicationLagSeconds": 10,
  "ProblemIgnoreHostnameFilters": [],
  "MaintenanceOwner": "orchestrator",
  "RecoveryPeriodBlockSeconds": 3600,
  "RecoveryIgnoreHostnameFilters": [],
  "RecoverMasterClusterFilters": ["*"],
  "RecoverIntermediateMasterClusterFilters": ["*"],
  "OnFailureDetectionProcesses": [],
  "PreGracefulTakeoverProcesses": [],
  "PreFailoverProcesses": [],
  "PostFailoverProcesses": [],
  "PostUnsuccessfulFailoverProcesses": [],
  "PostMasterFailoverProcesses": [],
  "PostIntermediateMasterFailoverProcesses": [],
  "CoMasterRecoveryMustPromoteOtherCoMaster": true,
  "DetachLostReplicasAfterMasterFailover": true,
  "DetachLostIntermediateMasterReplicasAfterFailover": true,
  "ApplyMySQLPromotionAfterMasterFailover": true,
  "PreventCrossDataCenterMasterFailover": false,
  "PreventCrossRegionMasterFailover": false,
  "MasterFailoverDetachReplicaMasterHost": false,
  "MasterFailoverLostInstancesDowntimeMinutes": 0,
  "PostponeReplicaRecoveryOnLagMinutes": 0
}
```

## Choosing the Right MySQL HA Solution

Selecting between InnoDB Cluster, Percona XtraDB Cluster, and Orchestrator comes down to three key questions:

**1. How much data can you afford to lose?** If the answer is zero, choose InnoDB Cluster or Percona XtraDB Cluster — both offer synchronous replication with guaranteed consistency. If you can tolerate seconds of potential data loss in exchange for simpler operations and better write performance on the primary, Orchestrator with semi-synchronous replication is a viable option.

**2. Do you need multi-master writes?** Percona XtraDB Cluster is the only solution that truly supports writes to any node. InnoDB Cluster supports multi-primary mode, but write conflicts require application-level handling. Orchestrator manages single-primary topologies only.

**3. What's your existing MySQL setup?** If you're starting fresh, InnoDB Cluster or PXC provide turnkey HA. If you have established MySQL replication with dozens of replicas across data centers, Orchestrator can automate failover without requiring a replication architecture change.

## Why Self-Host Your MySQL High Availability Infrastructure?

Running your own MySQL high availability cluster gives you complete control over data residency, failover behavior, and operational procedures. Cloud-managed MySQL services (Amazon RDS, Google Cloud SQL, Azure Database for MySQL) abstract away HA complexity but come with significant trade-offs: vendor lock-in, limited configuration options, and costs that scale linearly with usage.

Self-hosted MySQL HA eliminates per-instance licensing fees and gives you full visibility into replication lag, failover timing, and cluster health. You can tune Group Replication parameters, adjust Galera flow control thresholds, or customize Orchestrator recovery policies to match your exact workload characteristics — flexibility that managed services simply cannot offer.

For organizations handling sensitive data, self-hosting MySQL HA ensures that replication traffic never leaves your infrastructure. This is critical for industries with strict data residency requirements (healthcare, finance, government) where sending transaction data through a cloud provider's replication layer may violate compliance mandates.

For database tuning and performance optimization, see our [database tuning guide](../2026-05-03-self-hosted-database-tuning-mysqltuner-pgtune-pgtune-ng-guide/). For zero-downtime schema changes in your HA cluster, check our [MySQL schema migration comparison](../2026-04-29-gh-ost-vs-pt-online-schema-change-vs-mariadb-online-ddl-zero-downtime-mysql-schema-migration/). And for managing replication topologies at scale, our [MySQL replication topology guide](../2026-05-09-self-hosted-mysql-replication-topology-management-orchestrator-pmm-shell-guide/) covers the operational side.

## Frequently Asked Questions

### What is the difference between MySQL InnoDB Cluster and Percona XtraDB Cluster?

MySQL InnoDB Cluster uses Group Replication with the Paxos consensus protocol for synchronous replication, while Percona XtraDB Cluster uses Galera's virtual synchrony protocol. InnoDB Cluster is tightly integrated with MySQL Shell and MySQL Router for a unified experience. PXC offers true multi-master writes with parallel applying, making it better for write-heavy workloads. Both require a minimum of 3 nodes and provide zero data loss failover.

### Can I use MySQL Orchestrator with Percona XtraDB Cluster?

No. MySQL Orchestrator manages asynchronous replication topologies, while Percona XtraDB Cluster uses synchronous Galera replication. They serve different HA paradigms. Orchestrator works with standard MySQL replication (async or semi-synchronous), while PXC has its own built-in failover through Galera's quorum mechanism.

### How many nodes do I need for MySQL high availability?

For InnoDB Cluster and Percona XtraDB Cluster, you need a minimum of 3 nodes to maintain quorum during a single-node failure. For Orchestrator with async replication, you need at least 2 nodes (1 primary + 1 replica), but 3+ is recommended to ensure a replica is always available for promotion.

### Does MySQL InnoDB Cluster support multi-primary mode in production?

Yes, but with caveats. Multi-primary mode allows writes to any node, but applications must handle potential conflicts (e.g., two nodes updating the same row simultaneously). For most workloads, single-primary mode is recommended — it's simpler to operate and avoids the complexity of distributed conflict resolution.

### What happens to a MySQL InnoDB Cluster when a node loses quorum?

When a node cannot reach a majority of the cluster, it enters a read-only state to prevent split-brain scenarios. The remaining nodes with quorum continue accepting writes. If the cluster loses quorum entirely (e.g., 2 of 3 nodes fail), the cluster becomes read-only until the missing nodes are restored or the cluster is manually bootstrapped from a surviving node.

### How do I monitor MySQL Orchestrator?

MySQL Orchestrator provides a web UI at port 3000 (default) showing the full replication topology, node health status, and recent failover events. It also exposes a REST API for programmatic access and integrates with Prometheus for metrics collection. You can configure email or webhook notifications for failover events.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MySQL High Availability: InnoDB Cluster vs Percona XtraDB Cluster vs Orchestrator",
  "description": "Compare MySQL InnoDB Cluster, Percona XtraDB Cluster, and MySQL Orchestrator for self-hosted high availability. Includes Docker Compose configs, feature comparison, and deployment guides.",
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
