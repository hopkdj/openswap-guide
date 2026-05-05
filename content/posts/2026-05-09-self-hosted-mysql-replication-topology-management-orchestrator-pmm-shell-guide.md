---
title: "Self-Hosted MySQL Replication Topology Management: Orchestrator vs PMM vs MySQL Shell 2026"
date: 2026-05-09T09:00:00Z
tags: ["mysql", "database", "replication", "high-availability", "topology", "orchestration"]
draft: false
---

MySQL replication is the foundation of database high availability, but managing replication topologies at scale quickly becomes complex. Manual failover, replication lag monitoring, and topology changes require specialized tools. This guide compares three self-hosted solutions for MySQL replication topology management that automate failover, visualize replication graphs, and keep your databases running.

## The Challenge of MySQL Replication Management

Running MySQL in production means dealing with:
- **Primary failover**: When the primary goes down, promoting a replica without data loss
- **Replication lag**: Detecting and resolving delays between primary and replicas
- **Topology changes**: Adding/removing replicas, switching from star to chain topology
- **GTID management**: Tracking Global Transaction IDs during failover events
- **Semi-sync configuration**: Balancing consistency vs. latency with synchronous replication

Without proper tooling, a primary failure means minutes of manual intervention — or worse, split-brain scenarios where two nodes believe they are primary.

## Comparison Overview

| Feature | MySQL Orchestrator | Percona PMM | MySQL Shell |
|---------|-------------------|-------------|-------------|
| Automatic failover | Yes | No (monitoring only) | Semi-automatic |
| Topology visualization | Web UI | Grafana dashboards | CLI text output |
| Replication lag alerting | Built-in | Advanced (Prometheus) | Manual checks |
| GTID-aware failover | Yes | N/A | Yes |
| Semi-sync management | Yes | Monitoring only | Manual configuration |
| API access | REST API | Grafana API | Python/JS scripting |
| Cluster support | 1000+ nodes | Limited by Prometheus | Per-session |
| Open source | Apache 2.0 | Apache 2.0 | GPL v2 |
| GitHub Stars | 5,700+ | 1,000+ | Bundled with MySQL |

## MySQL Orchestrator: Automated Topology Management

[MySQL Orchestrator](https://github.com/openark/orchestrator) (5,700+ GitHub stars) is the gold standard for MySQL replication topology management. It discovers your replication graph automatically, provides a web-based topology visualization, and supports both manual and automatic failover with safety checks.

### How Orchestrator Works

Orchestrator connects to each MySQL instance, reads replication metadata (`SHOW SLAVE STATUS`, `SHOW MASTER STATUS`), and builds a complete topology graph. It stores this graph in a backend database (SQLite, MySQL, or Consul) and exposes it via REST API and web UI.

When a failover is triggered, Orchestrator:
1. Detects the primary failure through health checks
2. Identifies the most up-to-date replica using GTID position
3. Promotes the selected replica with `CHANGE MASTER TO`
4. Reconfigures remaining replicas to point to the new primary
5. Updates topology visualization and sends alerts

### Docker Compose Deployment

```yaml
version: "3.8"

services:
  orchestrator:
    image: ghcr.io/openark/orchestrator:latest
    ports:
      - "3000:3000"
    volumes:
      - ./orchestrator/conf:/usr/local/orchestrator/resources/conf
      - ./orchestrator/data:/usr/local/orchestrator/data
    environment:
      - ORCHESTRATOR_DEBUG=false
      - ORCHESTRATOR_BACKEND_DB_TYPE=sqlite
      - ORCHESTRATOR_DISCOVER_SEEDS=mysql-primary:3306,mysql-replica1:3306
    restart: unless-stopped
    depends_on:
      - mysql-primary

  mysql-primary:
    image: mysql:8.4
    ports:
      - "3306:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_REPLICATION_USER=repl
      - MYSQL_REPLICATION_PASSWORD=replpass
    volumes:
      - ./mysql-primary/data:/var/lib/mysql
      - ./mysql-primary/conf.d:/etc/mysql/conf.d
    command: >
      --server-id=1
      --gtid-mode=ON
      --enforce-gtid-consistency=ON
      --log-bin=mysql-bin
      --binlog-format=ROW
      --semi-sync-master-enabled=1

networks:
  default:
    driver: bridge
```

### Orchestrator Configuration

```json
{
  "Debug": false,
  "MySQLTopologyUser": "orchestrator",
  "MySQLTopologyPassword": "orch_pass",
  "DetectionPeriodSeconds": 5,
  "InstancePollSeconds": 5,
  "ForgetUnseenAgentDifferential": 50,
  "DiscoverByShowSlaveHosts": true,
  "FailureDetectionPeriodBlockMinutes": 60,
  "RecoveryPeriodBlockSeconds": 300,
  "RecoveryIgnoreHostnameFilters": [],
  "ApplyMySQLPromotionAfterMasterFailover": true,
  "MasterFailoverDetachReplicaMasterHost": true,
  "MasterFailoverLostInstancesDowntimeMinutes": 10
}
```

Key failover safety settings:
- `RecoveryPeriodBlockSeconds`: Prevents repeated failover attempts (default: 300s)
- `FailureDetectionPeriodBlockMinutes`: Cooldown after a detected failure
- `ApplyMySQLPromotionAfterMasterFailover`: Runs `RESET SLAVE ALL` on promoted replica

## Percona Monitoring and Management: Replication Observability

[Percona PMM](https://github.com/percona/pmm) (1,000+ GitHub stars) provides deep visibility into MySQL replication health through Grafana dashboards. While it doesn't perform automatic failover, it excels at detecting replication issues before they become outages.

### Replication Monitoring Features

PMM collects over 1,000 MySQL metrics including:
- Replication lag (seconds behind primary)
- Relay log growth rate
- SQL thread and I/O thread status
- GTID execution sets
- Semi-sync replication status
- Binlog write latency

### Docker Compose for PMM Server

```yaml
version: "3.8"

services:
  pmm-server:
    image: percona/pmm-server:2
    container_name: pmm-server
    hostname: pmm-server
    ports:
      - "443:443"
    volumes:
      - pmm-data:/srv
    environment:
      - PERCONA_TEST_DBAAS=1
      - PMM_AGENT_CONFIG_FILE=/usr/local/percona/pmm2/config/pmm-agent.yaml
    restart: unless-stopped

volumes:
  pmm-data: {}
```

### Adding MySQL Instances to PMM

```bash
# Install PMM client on each MySQL host
docker pull percona/pmm-client:2

# Register MySQL instance with PMM server
docker run -d   -p 42000:42000   --name pmm-client   -e PMM_AGENT_SERVER_URL=https://pmm-server:443   -e PMM_AGENT_SERVER_INSECURE_TLS=1   -e PMM_AGENT_CONFIG_FILE=/usr/local/percona/pmm2/config/pmm-agent.yaml   percona/pmm-client:2

# Add MySQL monitoring
pmm-admin add mysql --username=pmm --password=pmpass --query-source=slowlog mysql-primary:3306
```

PMM's replication dashboard shows lag trends, thread status history, and binlog throughput — essential for capacity planning and performance tuning.

## MySQL Shell: Scripted Topology Management

MySQL Shell (bundled with MySQL 8.0+) provides a JavaScript/Python interface for managing InnoDB Cluster and replication topologies. It supports the AdminAPI, which enables programmatic cluster management including automated failover through MySQL Router.

### InnoDB Cluster Setup

```python
import mysqlsh

# Connect to the primary instance
shell.connect('admin@mysql-primary:3306')

# Create an InnoDB Cluster
cluster = dba.create_cluster('production')

# Add replicas
cluster.add_instance('admin@mysql-replica1:3306')
cluster.add_instance('admin@mysql-replica2:3306')

# Check cluster status
cluster.status()

# Perform a controlled switchover
cluster.set_primary_instance('mysql-replica1:3306')
```

### Docker Compose with InnoDB Cluster

```yaml
version: "3.8"

services:
  mysql-1:
    image: mysql:8.4
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_USER=icadmin
      - MYSQL_PASSWORD=icpass
    volumes:
      - ./mysql-1/data:/var/lib/mysql
    command: >
      --server-id=1
      --gtid-mode=ON
      --enforce-gtid-consistency=ON
      --log-bin=mysql-bin
      --binlog-format=ROW
      --mysqlx=ON
      --clone=ON

  mysql-2:
    image: mysql:8.4
    environment:
      - MYSQL_ROOT_PASSWORD=rootpass
      - MYSQL_USER=icadmin
      - MYSQL_PASSWORD=icpass
    volumes:
      - ./mysql-2/data:/var/lib/mysql
    depends_on:
      - mysql-1
    command: >
      --server-id=2
      --gtid-mode=ON
      --enforce-gtid-consistency=ON
      --log-bin=mysql-bin
      --binlog-format=ROW

  mysql-shell:
    image: mysql/mysql-shell:latest
    depends_on:
      - mysql-1
      - mysql-2
    entrypoint: ["mysqlsh", "--js"]
```

## Decision Matrix

**Choose MySQL Orchestrator** when:
- You need automated failover with safety guarantees
- You manage 10+ MySQL instances with complex topologies
- You want a web-based topology map for operations teams
- You operate mixed MySQL versions and need unified management

**Choose Percona PMM** when:
- Your priority is observability over automation
- You already use Grafana/Prometheus for monitoring
- You need deep query-level replication analysis
- You want historical trend analysis for capacity planning

**Choose MySQL Shell/InnoDB Cluster** when:
- You run MySQL 8.0+ exclusively
- You want native MySQL Group Replication
- You prefer programmatic management via Python/JS APIs
- You need integrated MySQL Router for connection routing

For more database management guides, see our [database monitoring comparison](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/), [database query profiling tools](../2026-04-23-self-hosted-database-query-profiling-optimization-tools-guide-2026/), and [version-controlled databases guide](../2026-04-21-dolt-vs-terminusdb-vs-couchdb-version-controlled-databases-guide-2026/).

## Why Self-Host Replication Management?

Commercial MySQL management tools like Amazon RDS Multi-AZ or Google Cloud SQL handle failover automatically but lock you into specific cloud providers and charge premium pricing. Self-hosted replication management tools give you the same automation capabilities on any infrastructure — bare metal, VMs, or Kubernetes — without vendor lock-in.

For organizations running MySQL across multiple data centers or hybrid cloud environments, self-hosted tools provide a unified management layer that works everywhere. MySQL Orchestrator's REST API integrates with existing runbook automation, while PMM's Grafana dashboards fit into existing observability stacks.

Cost comparison: A managed MySQL service with automatic failover typically costs 2-3× the base database price. Self-hosted Orchestrator + PMM on a small monitoring server ($30-50/month) serves hundreds of MySQL instances at a fraction of the managed service cost.

Migration from manual to automated replication management typically takes one to two sprint cycles. Start by deploying Orchestrator in read-only discovery mode to map your existing topology, then gradually enable semi-automatic failover with operator approval before switching to full automation.

## FAQ

### Can Orchestrator perform automatic failover without human approval?

Yes. Configure `RecoveryPeriodBlockSeconds` and the detection settings to enable fully automatic failover. However, most production deployments use semi-automatic mode where Orchestrator detects failures and recommends actions, but requires operator approval via the REST API before executing failover.

### What is the difference between Orchestrator and MySQL InnoDB Cluster?

Orchestrator works with traditional MySQL replication (asynchronous or semi-synchronous) and manages topology through external coordination. InnoDB Cluster uses MySQL Group Replication (synchronous, Paxos-based consensus) with built-in failure detection. Orchestrator is more flexible with existing deployments; InnoDB Cluster requires MySQL 8.0+ and Group Replication.

### How does PMM detect replication lag?

PMM reads the `Seconds_Behind_Master` value from `SHOW SLAVE STATUS` on each replica, combined with GTID position comparison against the primary. It also monitors relay log apply rate to predict when lag will resolve.

### Can I use Orchestrator with MariaDB?

Orchestrator has experimental MariaDB support, but it's primarily designed for MySQL. MariaDB has its own MaxScale proxy with similar topology management capabilities. For MariaDB-specific deployments, consider MaxScale or Galera Cluster management tools.

### How do I handle split-brain scenarios during failover?

Orchestrator uses GTID-based position comparison to ensure only the most up-to-date replica is promoted. It also implements a `RecoveryPeriodBlockSeconds` cooldown to prevent cascading failovers. For additional safety, enable semi-synchronous replication with `rpl_semi_sync_master_wait_point=AFTER_SYNC` to ensure at least one replica has acknowledged each transaction before the primary commits.

### What monitoring metrics should I track for replication health?

Critical metrics include: replication lag (should be <1s for synchronous workloads), relay log size (growth indicates lag), SQL thread running status, IO thread running status, and GTID execution set comparison between primary and replicas. PMM provides all of these in pre-built Grafana dashboards.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted MySQL Replication Topology Management: Orchestrator vs PMM vs MySQL Shell 2026",
  "description": "Compare MySQL replication management tools: Orchestrator for automated failover, Percona PMM for observability, and MySQL Shell for programmatic cluster management.",
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
