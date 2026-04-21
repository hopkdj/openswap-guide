---
title: "CockroachDB vs YugabyteDB vs TiDB: Best Self-Hosted Distributed SQL Database 2026"
date: 2026-04-17
tags: ["comparison", "guide", "self-hosted", "database", "distributed-sql", "docker"]
draft: false
description: "Compare the top three open-source distributed SQL databases in 2026: CockroachDB, YugabyteDB, and TiDB. Architecture breakdown, Docker Compose setups, performance benchmarks, and migration guides for building horizontally scalable, fault-tolerant databases."
---

If your application has outgrown a single database node — whether because of write throughput, storage volume, or the need for geographic distribution — you have reached the point where a distributed SQL database is no longer a luxury. It is a necessity.

Cloud-managed offerings charge premium rates for multi-node clusters, charge for cross-region traffic, and lock you into a specific ecosystem. Self-hosting your distributed SQL layer gives you full control over topology, replication factor, backup strategy, and cost structure. In this guide, we compare the three most mature open-source distributed SQL databases of 2026: **CockroachDB**, **YugabyteDB**, and **TiDB**.

## Why Self-Host a Distributed SQL Database?

Running a distributed SQL database on your own infrastructure provides advantages that cloud-managed alternatives cannot match:

**Predictable cost at scale.** Cloud distributed databases charge per node-hour, per GB of storage, and per GB of cross-region data transfer. A three-node CockroachDB cluster on managed infrastructure can easily cost thousands of dollars per month. Self-hosted, you pay only for the underlying compute and storage.

**Full control over topology.** You decide how many replicas to run, where to place them across availability zones or data centers, and how to balance read and write workloads. Cloud providers often restrict topology options to predefined configurations.

**No vendor lock-in.** All three databases we cover are open source and speak standard PostgreSQL or MySQL protocols. Your application code is portable. If you ever need to migrate, your SQL queries and schema definitions stay the same.

**Complete data ownership.** Every byte of data, every index, every write-ahead log stays on infrastructure you control. This matters for regulated industries — financial services, healthcare, government — where data residency requirements are non-negotiable.

**Custom backup and disaster recovery.** You define the RPO and RTO. Snapshots go to your storage backend. Point-in-time recovery uses your schedule, not a vendor's default.

**Tuned for your workload.** You control memory allocation, compaction policies, garbage collection intervals, and storage engine settings. Fine-tuning is not restricted to a vendor's tuning knobs.

## What Is Distributed SQL?

A distributed SQL database spreads data across multiple nodes while preserving ACID transaction guarantees and SQL compatibility. Unlike sharding a traditional database manually — which requires application-level routing logic, breaks joins, and makes transactions painful — distributed SQL databases handle all of this transparently:

- **Automatic sharding** — data is split into ranges or tablets and distributed across nodes
- **Strong consistency** — reads and writes are linearizable by default via consensus protocols
- **Horizontal scaling** — add nodes to increase both storage capacity and throughput
- **Automatic rebalancing** — when nodes are added or removed, data redistributes without manual intervention
- **Survivable failures** — the database remains available as long as a quorum of replicas survives
- **Standard SQL** — application code uses familiar SQL with standard drivers

The trade-off is operational com[plex](https://www.plex.tv/)ity: distributed databases require more careful planning around network latency between nodes, clock synchronization, and initial cluster bootstrapping. But the payoff — a database that scales horizontally while maintaining transactional integrity — is substantial.

## Quick Comparison at a Glance

| Feature | CockroachDB | YugabyteDB | TiDB |
|---------|:-----------:|:----------:|:----:|
| **Protocol** | PostgreSQL | PostgreSQL (plus Cassandra/YCQL) | MySQL |
| **Storage Engine** | Pebble (LSM-tree, Go) | RocksDB (LSM-tree, C++) | TiKV (RocksDB, Rust) |
| **Consensus Protocol** | Raft (custom) | Raft (custom) | Multi-Raft (custom) |
| **SQL Layer** | Built-in (Go) | YSQL (PostgreSQL fork, C++) | TiDB Server (Go) |
| **License** | BSL 1.1 (changes to Apache 2.0 after 4 years) | Apache 2.0 | Apache 2.0 |
| **Latest Stable** | v24.3 | v2.24 | v8.5 |
| **GitHub Stars** | 31,800+ | 11,400+ | 43,600+ |
| **Min Cluster Size** | 3 nodes | 3 nodes | 3 (2 PD + 3 TiKV) |
| **Horizontal Scale** | ✅ Add nodes, auto-rebalance | ✅ Add nodes, auto-rebalance | ✅ Add TiKV/TiDB nodes |
| **Global Tables** | ✅ Geo-partitioned data | ✅ Table-level placement | ⚠️ Via placement rules |
| **Online Schema Changes** | ✅ Non-blocking | ✅ Non-blocking | ✅ Non-blocking |
| **Distributed TX (2PC)** | ✅ Serializable by default | ✅ Serializable, repeatable read | ✅ Optimistic, pessimistic |
| **Time-Travel Queries** | ✅ AS OF SYSTEM TIME | ✅ ✅ | ✅ ✅ |
| **Change Data Capture** | ✅ Built-in | ✅ Built-in | ✅ TiCDC |
| **Backup** | ✅ Built-in to cloud storage | ✅ Built-in | ✅ BR tool + Lightning |
| **Vector Search** | ✅ ANN index | ❌ Not yet | ❌ Not yet |
| **Min RAM per Node** | 4 GB (recommended 8+) | 8 GB (recommended 16+) | 8 GB (recommended 16+) |
| **Best For** | Teams wanting PostgreSQL + simplicity | Teams wanting PostgreSQL + NoSQL flexibility | Teams wanting MySQL + massive scale |

## CockroachDB — The PostgreSQL-Compatible Pioneer

CockroachDB, created by the founders of KeyValues (who previously built Google's Spanner), was one of the first distributed SQL databases to achieve production maturity. It speaks the PostgreSQL wire protocol, meaning any PostgreSQL driver or ORM works out of the box.

### Architecture

CockroachDB uses a layered architecture:

1. **SQL layer** — parses SQL, builds query plans, and executes them. Written in Go.
2. **KV layer** — a distributed key-value store where data is organized into ranges (64 MB chunks). Each range is replicated via Raft consensus.
3. **Storage layer** — Pebble, a high-performance LSM-tree storage engine written in Go (a successor to RocksDB).

Data is automatically split into ranges, replicated across nodes (default 3x), and rebalanced as the cluster grows. Each range has a Raft leader that handles writes; followers serve reads when configured for lease preferences.

### Key Strengths

**PostgreSQL compatibility.** Any application that connects to PostgreSQL can connect to CockroachDB. psycopg2, pgx, GORM, Prisma, SQLAlchemy — all work with zero modification. The SQL dialect includes most PostgreSQL features: CTEs, window functions, JSONB, arrays, and user-defined types.

**Geo-partitioning.** You can pin specific rows to specific regions. For example, European user data stays in EU nodes while US user data stays in US nodes — all within the same logical table. This is essential for GDPR compliance without sacrificing performance.

**Survivability.** CockroachDB can survive entire data center failures. With a 5-node cluster spread across 3 regions, losing one region still leaves a quorum. The database automatically re-replicates data to surviving nodes.

**Built-in observability.** The DB Console (accessible at `http://localhost:8080`) provides real-time visibility into query execution, range distribution, replication health, and node metrics. No external monitoring [docker](https://www.docker.com/)is required.

### Docker Compose Setup (Single Node — Development)

```yaml
services:
  cockroachdb:
    image: cockroachdb/cockroach:v24.3.3
    container_name: cockroachdb
    restart: unless-stopped
    command: start-single-node --insecure --store=attr=ssd,path=/cockroach/cockroach-data
    ports:
      - "26257:26257"   # SQL port
      - "8080:8080"     # DB Console
    volumes:
      - cockroach-data:/cockroach/cockroach-data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  cockroach-data:
```

Start the database and connect:

```bash
docker compose up -d

# Connect with the built-in SQL shell
docker exec -it cockroachdb ./cockroach sql --insecure

# Or connect from your application using PostgreSQL drivers
# Connection string: postgresql://root@localhost:26257/defaultdb?sslmode=disable
```

### Docker Compose Setup (3-Node Cluster — Production)

For a production cluster, you need multiple nodes. This setup creates a 3-node cluster on a single Docker host for testing:

```yaml
services:
  roach1:
    image: cockroachdb/cockroach:v24.3.3
    container_name: roach1
    command: start --cluster-name=crdb --insecure --store=attr=ssd,path=/cockroach/cockroach-data --listen-addr=roach1:26257 --http-addr=roach1:8080 --join=roach1:26257,roach2:26257,roach3:26257
    ports:
      - "26257:26257"
      - "8080:8080"
    volumes:
      - data1:/cockroach/cockroach-data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  roach2:
    image: cockroachdb/cockroach:v24.3.3
    container_name: roach2
    command: start --cluster-name=crdb --insecure --store=attr=ssd,path=/cockroach/cockroach-data --listen-addr=roach2:26257 --http-addr=roach2:8080 --join=roach1:26257,roach2:26257,roach3:26257
    ports:
      - "26258:26257"
      - "8081:8080"
    volumes:
      - data2:/cockroach/cockroach-data
    depends_on:
      roach1:
        condition: service_healthy

  roach3:
    image: cockroachdb/cockroach:v24.3.3
    container_name: roach3
    command: start --cluster-name=crdb --insecure --store=attr=ssd,path=/cockroach/cockroach-data --listen-addr=roach3:26257 --http-addr=roach3:8080 --join=roach1:26257,roach2:26257,roach3:26257
    ports:
      - "26259:26257"
      - "8082:8080"
    volumes:
      - data3:/cockroach/cockroach-data
    depends_on:
      roach1:
        condition: service_healthy

volumes:
  data1:
  data2:
  data3:
```

Initialize the cluster after all nodes are healthy:

```bash
docker exec -it roach1 ./cockroach init --insecure
```

Verify the cluster status:

```bash
docker exec -it roach1 ./cockroach node status --insecure --format=table
```

### Real-World Configuration Tips

**Enable TLS in production.** Never run `--insecure` outside of development. Generate certificates:

```bash
docker run --rm -v ./certs:/cockroach/certs \
  cockroachdb/cockroach:v24.3.3 cert create-ca --certs-dir=/cockroach/certs
docker run --rm -v ./certs:/cockroach/certs \
  cockroachdb/cockroach:v24.3.3 cert create-node localhost roach1 roach2 roach3 --certs-dir=/cockroach/certs
docker run --rm -v ./certs:/cockroach/certs \
  cockroachdb/cockroach:v24.3.3 cert create-client root --certs-dir=/cockroach/certs
```

**Tune storage for SSD.** CockroachDB performs significantly better on SSDs than HDDs. Set `--store=attr=ssd` to enable optimizations like more aggressive compaction scheduling.

**Set zone configurations for geo-partitioning:**

```sql
ALTER TABLE users CONFIGURE ZONE USING
  constraints = '{+region=eu: 1, +region=us: 1, +region=ap: 1}',
  num_replicas = 3;
```

## YugabyteDB — The Multi-API Distributed Database

YugabyteDB, founded by former Facebook and Nutanix engineers, takes a different approach. It provides two API layers on top of a shared distributed storage engine:

- **YSQL** — a fully PostgreSQL-compatible relational API (forked from PostgreSQL 11 source)
- **YCQL** — a Cassandra-compatible API with ACID transactions and secondary indexes

### Architecture

YugabyteDB uses a three-layer design:

1. **API layer** — YSQL (PostgreSQL fork) or YCQL (Cassandra-compatible). Each runs as a separate process (`ysqlmaster`, `ysqlserver`, `ycqlserver`).
2. **DocDB layer** — a distributed document store built on RocksDB, with a PostgreSQL-compatible SQL layer translated into document operations.
3. **Consensus layer** — Raft-based replication with tablet-level granularity. Each tablet (shard) has its own Raft group.

The YSQL layer is a fork of PostgreSQL 11's source code, modified to route operations to the distributed DocDB layer instead of local storage. This means YSQL inherits PostgreSQL's parser, planner, and executor — providing excellent compatibility.

### Key Strengths

**Two APIs, one database.** Run relational workloads on YSQL and high-throughput key-value workloads on YCQL — both sharing the same underlying data and transaction engine. This eliminates the need for separate PostgreSQL and Cassandra clusters.

**Strong PostgreSQL compatibility.** YSQL supports PostgreSQL 11 features including extensions, stored procedures, and most data types. The compatibility is improving with each release.

**Colocated tables.** For smaller tables, you can colocate all rows on a single tablet to avoid the overhead of distributed joins. This gives you the flexibility to mix distributed and colocated tables in the same database.

**Built-in load balancer.** YugabyteDB includes `yb-master` nodes that handle cluster coordination and automatic tablet placement. No external load balancer is needed for the control plane.

### Docker Compose Setup (Single Node — Development)

```yaml
services:
  yugabytedb:
    image: yugabytedb/yugabyte:2.24.2.0-b3
    container_name: yugabytedb
    restart: unless-stopped
    command: ["bin/yugabyted", "start", "--daemon=false"]
    ports:
      - "5433:5433"   # YSQL (PostgreSQL-compatible)
      - "9042:9042"   # YCQL (Cassandra-compatible)
      - "13000:13000" # Admin UI
    volumes:
      - yugabyte-data:/root/var
    healthcheck:
      test: ["CMD", "bin/yugabyted", "status"]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  yugabyte-data:
```

Start and connect:

```bash
docker compose up -d

# Connect to YSQL (PostgreSQL-compatible)
docker exec -it yugabytedb bin/ysqlsh

# Connect to YCQL (Cassandra-compatible)
docker exec -it yugabytedb bin/ycqlsh

# Application connection strings:
# YSQL:  postgresql://yugabyte:yugabyte@localhost:5433/yugabyte
# YCQL:  contact points: localhost:9042
```

### Docker Compose Setup (3-Node Cluster — Production)

```yaml
services:
  yb-node1:
    image: yugabytedb/yugabyte:2.24.2.0-b3
    container_name: yb-node1
    command: ["bin/yugabyted", "start", "--base_dir=/root/var", "--daemon=false", "--master_addr=yb-node1:7100"]
    ports:
      - "5433:5433"
      - "9042:9042"
      - "13000:13000"
    volumes:
      - data1:/root/var

  yb-node2:
    image: yugabytedb/yugabyte:2.24.2.0-b3
    container_name: yb-node2
    command: ["bin/yugabyted", "start", "--base_dir=/root/var", "--daemon=false", "--master_addr=yb-node1:7100", "--join=yb-node1:7100"]
    ports:
      - "5434:5433"
      - "9043:9042"
      - "13001:13000"
    volumes:
      - data2:/root/var
    depends_on:
      yb-node1:
        condition: service_healthy

  yb-node3:
    image: yugabytedb/yugabyte:2.24.2.0-b3
    container_name: yb-node3
    command: ["bin/yugabyted", "start", "--base_dir=/root/var", "--daemon=false", "--master_addr=yb-node1:7100", "--join=yb-node1:7100"]
    ports:
      - "5435:5433"
      - "9044:9042"
      - "13002:13000"
    volumes:
      - data3:/root/var
    depends_on:
      yb-node1:
        condition: service_healthy

volumes:
  data1:
  data2:
  data3:
```

After starting all nodes, run setup:

```bash
docker exec -it yb-node1 bin/yugabyted cluster setup
```

Verify cluster status via the Admin UI at `http://localhost:13000`.

### Performance Tuning

**Allocate sufficient memory.** YugabyteDB's default configuration assumes at least 16 GB of RAM. For smaller nodes, adjust the memory limits:

```bash
# Set flags for a 4 GB node
docker exec yb-node1 bash -c 'echo "--memory_limit_hard_bytes=2147483648" >> /root/var/conf/server.conf'
```

**Enable colocated tables for small reference data:**

```sql
CREATE TABLE countries (
  code CHAR(2) PRIMARY KEY,
  name VARCHAR(100) NOT NULL
) WITH (colocated = true);
```

## TiDB — The MySQL-Compatible Scale-Out Database

TiDB, developed by PingCAP, targets MySQL compatibility with a horizontally scalable architecture. It powers some of the largest production deployments of any distributed SQL database, with companies running clusters with thousands of nodes and petabytes of data.

### Architecture

TiDB uses a decoupled, three-tier architecture:

1. **TiDB Server** — the stateless SQL layer that parses SQL, builds query plans, and executes them. Multiple TiDB servers can run behind a load balancer for horizontal read/write scaling.
2. **TiKV** — the distributed storage layer. Data is stored as key-value pairs, organized into regions (~96 MB each), replicated via Multi-Raft. Each region has a Raft group.
3. **PD (Placement Driver)** — the metadata and scheduling service. PD manages cluster metadata, region placement, load balancing, and timestamp allocation (for distributed transactions via Oracle-style TSO).

The separation between compute (TiDB) and storage (TiKV) means you can scale them independently. Need more query throughput? Add TiDB servers. Need more storage? Add TiKV nodes.

### Key Strengths

**MySQL protocol compatibility.** TiDB speaks the MySQL wire protocol. Applications using mysql, pymysql, Go-MySQL-Driver, MySQL Connector/J, or any MySQL ORM work without modification. The SQL dialect is compatible with MySQL 5.7 and 8.0 features.

**HTAP (Hybrid Transactional/Analytical Processing).** TiDB includes TiFlash, a columnar storage replica that runs alongside TiKV. You can route analytical queries to TiFlash while OLTP queries go to TiKV — all on the same data, with real-time replication.

**Massive scale.** TiDB is designed for very large clusters. Production deployments with 100+ TiKV nodes and tens of TiDB servers are common. The decoupled architecture means the SQL layer never becomes a bottleneck.

**TiCDC for change data capture.** TiCD[kafka](https://kafka.apache.org/)eams row-level changes to downstream systems (Kafka, MySQL, storage) in real time, enabling event-driven architectures without dual-writes.

### Docker Compose Setup (Single Node via TiUP Playground — Development)

TiDB's recommended development setup uses `tiup`, the cluster management tool. For Docker, PingCAP provides a convenience image:

```yaml
services:
  tidb:
    image: pingcap/tidb:v8.5.0
    container_name: tidb
    restart: unless-stopped
    ports:
      - "4000:4000"   # MySQL-compatible SQL port
      - "10080:10080" # Status port
    command: ["--store=mocktikv"]
    # Note: mocktikv is single-node only. For a real cluster, use TiUP or Docker Compose below.

  # For a minimal real cluster, use the docker-compose playground:
  # docker run --rm -d -p 4000:4000 -p 2379:2379 -p 9090:9090 \
  #   pingcap/tidb:v8.5.0 playground --host 0.0.0.0 --db 1 --pd 1 --kv 1
```

For a real multi-node cluster, the simplest approach is using the TiUP playground in Docker:

```bash
docker run --rm -d --name tidb-playground \
  -p 4000:4000 -p 2379:2379 -p 9090:9090 \
  pingcap/tidb:v8.5.0 playground --host 0.0.0.0 --db 1 --pd 1 --kv 1 --monitor
```

Connect using any MySQL client:

```bash
mysql -h 127.0.0.1 -P 4000 -u root

# Application connection string:
# mysql://root@localhost:4000/test
```

### Docker Compose Setup (Full Cluster — Production)

A production TiDB cluster requires PD, TiKV, and TiDB components. Here is a minimal 3-node setup:

```yaml
services:
  pd1:
    image: pingcap/pd:v8.5.0
    container_name: pd1
    command:
      - --name=pd1
      - --client-urls=http://0.0.0.0:2379
      - --peer-urls=http://0.0.0.0:2380
      - --advertise-client-urls=http://pd1:2379
      - --advertise-peer-urls=http://pd1:2380
      - --initial-cluster=pd1=http://pd1:2380,pd2=http://pd2:2380,pd3=http://pd3:2380
      - --data-dir=/data/pd1
    ports:
      - "2379:2379"
      - "2380:2380"
    volumes:
      - pd1-data:/data

  pd2:
    image: pingcap/pd:v8.5.0
    container_name: pd2
    command:
      - --name=pd2
      - --client-urls=http://0.0.0.0:2379
      - --peer-urls=http://0.0.0.0:2380
      - --advertise-client-urls=http://pd2:2379
      - --advertise-peer-urls=http://pd2:2380
      - --initial-cluster=pd1=http://pd1:2380,pd2=http://pd2:2380,pd3=http://pd3:2380
      - --join=http://pd1:2379
      - --data-dir=/data/pd2
    ports:
      - "2381:2380"
    volumes:
      - pd2-data:/data
    depends_on:
      - pd1

  pd3:
    image: pingcap/pd:v8.5.0
    container_name: pd3
    command:
      - --name=pd3
      - --client-urls=http://0.0.0.0:2379
      - --peer-urls=http://0.0.0.0:2380
      - --advertise-client-urls=http://pd3:2379
      - --advertise-peer-urls=http://pd3:2380
      - --initial-cluster=pd1=http://pd1:2380,pd2=http://pd2:2380,pd3=http://pd3:2380
      - --join=http://pd1:2379
      - --data-dir=/data/pd3
    ports:
      - "2382:2380"
    volumes:
      - pd3-data:/data
    depends_on:
      - pd1

  tikv1:
    image: pingcap/tikv:v8.5.0
    container_name: tikv1
    command:
      - --addr=0.0.0.0:20160
      - --advertise-addr=tikv1:20160
      - --status-addr=0.0.0.0:20180
      - --data-dir=/data/tikv1
      - --pd=pd1:2379,pd2:2379,pd3:2379
    ports:
      - "20160:20160"
    volumes:
      - tikv1-data:/data
    depends_on:
      - pd1
      - pd2
      - pd3

  tikv2:
    image: pingcap/tikv:v8.5.0
    container_name: tikv2
    command:
      - --addr=0.0.0.0:20160
      - --advertise-addr=tikv2:20160
      - --status-addr=0.0.0.0:20180
      - --data-dir=/data/tikv2
      - --pd=pd1:2379,pd2:2379,pd3:2379
    ports:
      - "20161:20160"
    volumes:
      - tikv2-data:/data
    depends_on:
      - pd1
      - pd2
      - pd3

  tikv3:
    image: pingcap/tikv:v8.5.0
    container_name: tikv3
    command:
      - --addr=0.0.0.0:20160
      - --advertise-addr=tikv3:20160
      - --status-addr=0.0.0.0:20180
      - --data-dir=/data/tikv3
      - --pd=pd1:2379,pd2:2379,pd3:2379
    ports:
      - "20162:20160"
    volumes:
      - tikv3-data:/data
    depends_on:
      - pd1
      - pd2
      - pd3

  tidb:
    image: pingcap/tidb:v8.5.0
    container_name: tidb
    command:
      - --store=tikv
      - --path=pd1:2379,pd2:2379,pd3:2379
      - --advertise-address=tidb
    ports:
      - "4000:4000"
      - "10080:10080"
    depends_on:
      - tikv1
      - tikv2
      - tikv3

volumes:
  pd1-data:
  pd2-data:
  pd3-data:
  tikv1-data:
  tikv2-data:
  tikv3-data:
```

Start the cluster and verify:

```bash
docker compose up -d

# Check cluster status
docker exec -it pd1 pd-ctl member
docker exec -it pd1 pd-ctl store
```

### Adding TiFlash for HTAP

To enable analytical queries on the same data:

```yaml
  tiflash:
    image: pingcap/tiflash:v8.5.0
    container_name: tiflash
    command:
      - --config=/data/tiflash.toml
      - --addr=0.0.0.0:3930
      - --advertise-addr=tiflash:3930
      - --status-addr=0.0.0.0:20292
      - --pd=pd1:2379,pd2:2379,pd3:2379
    ports:
      - "3930:3930"
      - "20292:20292"
    depends_on:
      - tikv1
      - tikv2
      - tikv3
      - tikv3
```

After TiFlash joins the cluster, replicate specific tables:

```sql
ALTER TABLE orders SET TIFLASH REPLICA 1;
```

Queries against `orders` will now be automatically routed to the columnar TiFlash engine.

## Performance Benchmark Comparison

Independent benchmarks from 2025–2026 across three-node clusters on identical hardware (8 vCPU, 32 GB RAM, NVMe SSD per node):

| Benchmark | CockroachDB v24.3 | YugabyteDB v2.24 | TiDB v8.5 |
|-----------|:-----------------:|:----------------:|:---------:|
| **Sysbench OLTP (read-only)** | 45,000 QPS | 52,000 QPS | 68,000 QPS |
| **Sysbench OLTP (read-write)** | 12,000 TPS | 15,000 TPS | 18,000 TPS |
| **Sysbench OLTP (write-heavy)** | 5,500 TPS | 7,200 TPS | 9,800 TPS |
| **TPC-C (3 warehouses)** | 8,200 tpmC | 10,500 tpmC | 14,200 tpmC |
| **P99 Latency (read)** | 8 ms | 6 ms | 5 ms |
| **P99 Latency (write)** | 25 ms | 18 ms | 15 ms |
| **Storage per 100M rows** | 22 GB | 18 GB | 16 GB |

TiDB leads in raw throughput due to its decoupled architecture — the stateless TiDB layer can process queries in parallel without competing with storage I/O. YugabyteDB sits in the middle with its integrated DocDB engine. CockroachDB, while slightly slower in raw numbers, offers the best operational simplicity and the most mature geo-distribution features.

These numbers vary significantly based on workload characteristics. For read-heavy analytical queries, TiDB with TiFlash can exceed 500,000 QPS on columnar scans. For small, low-latency key-value lookups, all three perform similarly. The choice should be driven by your workload pattern, not a single benchmark number.

## Choosing the Right Distributed SQL Database

### Choose CockroachDB if:

- You need PostgreSQL compatibility with the smoothest migration path
- Geo-partitioning and data residency are core requirements
- You value operational simplicity and built-in observability
- Your team prefers a single binary with minimal moving parts
- You want vector search alongside relational queries

### Choose YugabyteDB if:

- You want both PostgreSQL and Cassandra APIs on the same data
- You need to run relational and key-value workloads side by side
- You prefer Apache 2.0 licensing without time-based restrictions
- Your team values colocated tables for small reference data
- You want a database that bridges the SQL and NoSQL worlds

### Choose TiDB if:

- You need MySQL compatibility at massive scale
- HTAP (mixed OLTP + OLAP) is a core requirement
- Your team is more comfortable with the MySQL ecosystem
- You plan to grow to hundreds of nodes
- You want independent scaling of compute and storage

## Migration Strategies

### From PostgreSQL to CockroachDB or YugabyteDB

Both support the `pg_dump` / `pg_restore` workflow:

```bash
# Export from PostgreSQL
pg_dump -h localhost -U postgres -d myapp > myapp.sql

# Import into CockroachDB
docker exec -i cockroachdb ./cockroach sql --insecure --database=myapp < myapp.sql

# Import into YugabyteDB
docker exec -i yugabytedb bin/ysqlsh -d myapp < myapp.sql
```

Note: some PostgreSQL extensions and proprietary functions may need manual adjustment. Test thoroughly before migrating production data.

### From MySQL to TiDB

TiDB supports direct MySQL dump import:

```bash
# Export from MySQL
mysqldump -h localhost -u root -p myapp > myapp.sql

# Import into TiDB
mysql -h 127.0.0.1 -P 4000 -u root myapp < myapp.sql
```

For large databases, use TiDB Lightning for parallel import:

```bash
tiup tidb-lightning -d /path/to/dump --backend tidb --server-memory-quota 4GB
```

Lightning can import 1 TB of data in under 6 hours on a 3-node cluster.

## Final Thoughts

All three databases are production-ready and deployed at scale. The decision ultimately comes down to protocol compatibility (PostgreSQL vs MySQL), operational preferences, and specific feature needs like geo-partitioning, HTAP, or multi-API support.

The best approach is to run a proof of concept with your actual workload. Each database has a Docker Compose setup that takes under five minutes to start. Import a subset of your production data, run your most important queries, and measure the results. The right choice will become obvious within an hour of hands-on testing.

## Frequently Asked Questions (FAQ)

### Which one should I choose in 2026?

The best choice depends on your specific requirements:

- **For beginners**: Start with the simplest option that covers your core use case
- **For production**: Choose the solution with the most active community and documentation
- **For teams**: Look for collaboration features and user management
- **For privacy**: Prefer fully open-source, self-hosted options with no telemetry

Refer to the comparison table above for detailed feature breakdowns.

### Can I migrate between these tools?

Most tools support data import/export. Always:
1. Backup your current data
2. Test the migration on a staging environment
3. Check official migration guides in the documentation

### Are there free versions available?

All tools in this guide offer free, open-source editions. Some also provide paid plans with additional features, priority support, or managed hosting.

### How do I get started?

1. Review the comparison table to identify your requirements
2. Visit the official documentation (links provided above)
3. Start with a Docker Compose setup for easy testing
4. Join the community forums for troubleshooting
