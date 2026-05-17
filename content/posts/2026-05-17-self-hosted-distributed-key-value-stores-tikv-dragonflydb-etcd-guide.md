---
title: "Self-Hosted Distributed Key-Value Stores: TiKV vs DragonflyDB vs etcd"
date: "2026-05-17"
tags: ["database", "key-value-store", "distributed-systems", "self-hosted"]
draft: false
---

Modern distributed applications require key-value stores that scale horizontally, maintain strong consistency guarantees, and survive node failures. Traditional single-node solutions like Redis hit capacity limits under heavy write throughput, while purpose-built distributed KV stores like **TiKV**, **DragonflyDB**, and **etcd** address different points in the distributed data management spectrum. This guide compares these three self-hosted solutions for production deployments.

## Understanding Distributed Key-Value Store Architectures

Distributed key-value stores solve a fundamental problem: how to store and retrieve data reliably across multiple machines. Each system makes different trade-offs:

- **Consistency model** — strong consistency (linearizable reads) vs eventual consistency
- **Partitioning strategy** — automatic data sharding across nodes vs manual configuration
- **Transaction support** — multi-key ACID transactions vs single-key atomic operations
- **Durability guarantees** — Write-Ahead Logging (WAL) vs in-memory with replication
- **Storage engine** — disk-based (RocksDB/LSM-tree) vs in-memory with persistence

## TiKV: Distributed Transactional Key-Value Database

TiKV (16,600+ stars, part of the TiDB ecosystem) is a distributed transactional KV store built in Rust with the Raft consensus protocol. Originally designed as the storage layer for TiDB (distributed SQL database), TiKV operates independently as a general-purpose distributed KV store.

### Architecture

TiKV uses a multi-Raft architecture where data is divided into Regions (~96MB each), each managed by a Raft group with 3 replicas:

```yaml
# docker-compose.yml for TiKV cluster
version: "3.8"
services:
  pd:
    image: pingcap/pd:latest
    command:
      - --name=pd
      - --client-urls=http://0.0.0.0:2379
      - --peer-urls=http://0.0.0.0:2380
      - --advertise-client-urls=http://pd:2379
      - --advertise-peer-urls=http://pd:2380
      - --initial-cluster=pd=http://pd:2380
      - --data-dir=/data/pd
    volumes:
      - pd-data:/data
    ports:
      - "2379:2379"

  tikv1:
    image: pingcap/tikv:latest
    command:
      - --addr=0.0.0.0:20160
      - --advertise-addr=tikv1:20160
      - --status-addr=0.0.0.0:20180
      - --pd=pd:2379
      - --data-dir=/data/tikv
    volumes:
      - tikv1-data:/data
    depends_on:
      - pd
    ports:
      - "20160:20160"

  tikv2:
    image: pingcap/tikv:latest
    command:
      - --addr=0.0.0.0:20160
      - --advertise-addr=tikv2:20160
      - --status-addr=0.0.0.0:20180
      - --pd=pd:2379
      - --data-dir=/data/tikv
    volumes:
      - tikv2-data:/data
    depends_on:
      - pd

  tikv3:
    image: pingcap/tikv:latest
    command:
      - --addr=0.0.0.0:20160
      - --advertise-addr=tikv3:20160
      - --status-addr=0.0.0.0:20180
      - --pd=pd:2379
      - --data-dir=/data/tikv
    volumes:
      - tikv3-data:/data
    depends_on:
      - pd

volumes:
  pd-data:
  tikv1-data:
  tikv2-data:
  tikv3-data:
```

### Key Features

- **Raft-based replication** — strong consistency with automatic failover (tolerates N/2 node failures)
- **RocksDB storage engine** — LSM-tree on-disk storage with compaction and compression
- **Automatic region splitting** — data automatically splits and rebalances across nodes
- **Snapshot isolation** — multi-version concurrency control (MVCC) for transaction isolation
- **Raw and Transaction APIs** — both simple KV operations and multi-key ACID transactions
- **Placement Driver (PD)** — centralized metadata management for scheduling and load balancing

### TiKV Client Usage (Rust)

```rust
use tikv_client::{Config, TransactionClient};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let client = TransactionClient::new(
        vec!["pd:2379"],
        Config::default()
    ).await?;
    
    let mut txn = client.begin_optimistic().await?;
    txn.put("user:1001".to_owned(), b"alice".to_vec()).await?;
    txn.commit().await?;
    
    let txn = client.begin_optimistic().await?;
    let value = txn.get("user:1001".to_owned()).await?;
    println!("Value: {:?}", value);
    
    Ok(())
}
```

## DragonflyDB: In-Memory Multi-Threaded KV Store

DragonflyDB (21,000+ stars) is a modern in-memory KV store designed as a Redis-compatible drop-in replacement with multi-threaded architecture. Unlike traditional single-threaded Redis, DragonflyDB leverages all CPU cores for higher throughput.

### Docker Deployment

```yaml
version: "3.8"
services:
  dragonfly:
    image: docker.dragonflydb.io/dragonflydb/dragonfly
    container_name: dragonfly
    restart: unless-stopped
    ports:
      - "6379:6379"
    command:
      - --maxmemory=4gb
      - --dir=/data
      - --dbfilename=dragonfly.rdb
    volumes:
      - df-data:/data
    deploy:
      resources:
        limits:
          memory: 8G

volumes:
  df-data:
```

### Key Features

- **Multi-threaded architecture** — utilizes all CPU cores, achieving 25x throughput over Redis on the same hardware
- **Redis compatibility** — supports 95%+ of Redis commands with identical semantics
- **In-memory with persistence** — RDB snapshots and AOF logging for durability
- **Low latency** — sub-millisecond p99 latency under heavy load through lock-free data structures
- **Active-Active replication** — multi-primary replication for geo-distributed deployments
- **Memory-efficient** — uses a shared-nothing architecture with per-shard locking

## etcd: Distributed Key-Value Store for Configuration

etcd (47,000+ stars, CNCF graduated) is the foundational distributed KV store powering Kubernetes. It uses the Raft consensus protocol to provide a strongly consistent, highly available key-value store optimized for configuration data and service discovery.

### Docker Cluster Deployment

```yaml
version: "3.8"
services:
  etcd1:
    image: quay.io/coreos/etcd:v3.5.12
    command: >
      etcd
      --name etcd1
      --data-dir /etcd-data
      --listen-client-urls http://0.0.0.0:2379
      --advertise-client-urls http://etcd1:2379
      --listen-peer-urls http://0.0.0.0:2380
      --initial-advertise-peer-urls http://etcd1:2380
      --initial-cluster etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      --initial-cluster-token etcd-cluster
      --initial-cluster-state new
    volumes:
      - etcd1-data:/etcd-data
    ports:
      - "2379:2379"

  etcd2:
    image: quay.io/coreos/etcd:v3.5.12
    command: >
      etcd
      --name etcd2
      --data-dir /etcd-data
      --listen-client-urls http://0.0.0.0:2379
      --advertise-client-urls http://etcd2:2379
      --listen-peer-urls http://0.0.0.0:2380
      --initial-advertise-peer-urls http://etcd2:2380
      --initial-cluster etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      --initial-cluster-token etcd-cluster
      --initial-cluster-state new
    volumes:
      - etcd2-data:/etcd-data
    ports:
      - "2380:2379"

  etcd3:
    image: quay.io/coreos/etcd:v3.5.12
    command: >
      etcd
      --name etcd3
      --data-dir /etcd-data
      --listen-client-urls http://0.0.0.0:2379
      --advertise-client-urls http://etcd3:2379
      --listen-peer-urls http://0.0.0.0:2380
      --initial-advertise-peer-urls http://etcd3:2380
      --initial-cluster etcd1=http://etcd1:2380,etcd2=http://etcd2:2380,etcd3=http://etcd3:2380
      --initial-cluster-token etcd-cluster
      --initial-cluster-state new
    volumes:
      - etcd3-data:/etcd-data
    ports:
      - "2381:2379"

volumes:
  etcd1-data:
  etcd2-data:
  etcd3-data:
```

### Key Features

- **Raft consensus** — linearizable consistency with automatic leader election
- **Watch API** — efficient change notification for keys and key prefixes
- **gRPC interface** — native gRPC API with protobuf serialization
- **MVCC** — multi-version concurrency control for consistent reads
- **Lease mechanism** — TTL-based key expiration for service discovery
- **Compact operation** — history compaction to control storage growth

## Feature Comparison

| Feature | TiKV | DragonflyDB | etcd |
|---------|------|-------------|------|
| Primary use case | Distributed transactions | In-memory cache/DB | Configuration/service discovery |
| Consistency model | Strong (Raft) | Eventual (replication) | Strong (Raft) |
| Storage engine | RocksDB (disk) | In-memory + RDB/AOF | BoltDB + WAL (disk) |
| Max data size | Petabytes (scales with nodes) | Limited by RAM | ~8GB recommended |
| Transaction support | ACID multi-key | Single-key atomic | Conditional (Compare-And-Swap) |
| Language | Rust | C++ | Go |
| Protocol | gRPC + Raw/Transaction | Redis Protocol (RESP3) | gRPC + HTTP/JSON |
| Horizontal scaling | Automatic region splitting | Manual sharding | Not designed for data scaling |
| GitHub stars | 16,600+ | 21,000+ | 47,000+ |
| CNCF status | Graduated (via TiDB) | Community | Graduated |

## Performance Characteristics

**TiKV** excels at large-scale distributed transactions with strong consistency. A 3-node TiKV cluster handles 100,000+ QPS for simple KV operations with sub-10ms p99 latency. The RocksDB storage engine provides durable storage with configurable compression (Snappy, ZSTD, LZ4). Region auto-splitting ensures balanced data distribution as data grows.

**DragonflyDB** delivers the highest throughput for in-memory operations — up to 1.6 million ops/sec on a 4-core machine, compared to Redis's ~60,000 ops/sec on the same hardware. The multi-threaded, lock-free architecture eliminates the single-threaded bottleneck that limits traditional Redis deployments. Ideal for session stores, caching layers, and real-time leaderboards.

**etcd** is optimized for small-value, high-read scenarios (configuration data, service discovery). It handles 10,000+ writes/sec and 50,000+ reads/sec on modest hardware but is not designed for large-value storage. The recommended maximum store size is 8GB due to BoltDB's performance characteristics.

## Why Self-Host Distributed KV Stores?

Running distributed key-value stores on self-hosted infrastructure eliminates the data residency and latency concerns of managed services. For TiKV, self-hosting gives you full control over data placement policies, region scheduling, and replication factors — critical for compliance requirements in finance and healthcare. DragonflyDB's multi-threaded architecture delivers better price-performance on bare-metal servers compared to managed Redis alternatives, reducing infrastructure costs by 40-60% for high-throughput caching workloads. Self-hosted etcd provides the foundation for building Kubernetes-like control planes on bare-metal infrastructure, without the per-node pricing of managed alternatives.

For database schema management on top of these stores, see our [database migration tools guide](../2026-05-14-self-hosted-lightweight-database-migrations-goose-dbmate-atlas-guide/). For distributed SQL databases that can use TiKV as a storage layer, our [distributed SQL comparison](../cockroachdb-vs-yugabyte-vs-tidb-distributed-sql-guide-2026/) covers the options. If you need etcd cluster management tools, check our [etcd management guide](../2026-05-13-self-hosted-etcd-management-uis-etcdkeeper-etcd-browser-etcd-manager-guide/).

## FAQ

### What is the difference between TiKV and Redis?

TiKV is a distributed, disk-based key-value store with strong consistency (Raft consensus) and multi-key ACID transaction support. Redis is an in-memory, single-threaded (traditionally) key-value store optimized for low-latency caching with eventual consistency across replicas. TiKV scales horizontally to petabytes of data across many nodes, while Redis is limited by available RAM on a single node (or requires manual sharding via Redis Cluster). Choose TiKV for persistent, transactional data storage; choose Redis (or DragonflyDB as a faster alternative) for caching and ephemeral data.

### Can DragonflyDB replace Redis in my application?

DragonflyDB is designed as a near drop-in replacement for Redis, supporting 95%+ of Redis commands with identical semantics. Most applications can switch by changing the connection endpoint from Redis to DragonflyDB without code changes. However, some advanced Redis features like Redis Modules, Lua scripting with complex dependencies, and Streams with consumer groups may have partial or no support. Test your specific command set before full migration.

### Why is etcd limited to ~8GB of data?

etcd uses BoltDB (a B-tree storage engine) for persistence, which stores the entire database in memory-mapped files. As data grows, compaction and snapshot operations become increasingly expensive, degrading performance. The Kubernetes project recommends keeping etcd data under 8GB because etcd is designed for configuration and metadata storage, not as a general-purpose data store. For larger datasets, use TiKV or a dedicated database.

### How does TiKV achieve horizontal scalability?

TiKV divides data into Regions (default ~96MB each), each managed by a Raft group. When a Region grows beyond the size threshold, it splits into two Regions that can be scheduled on different nodes. The Placement Driver (PD) component monitors cluster load and automatically balances Regions across TiKV nodes through leader transfer and Region migration. Adding a new TiKV node triggers automatic rebalancing, with PD migrating Regions to utilize the new capacity.

### Can I use etcd as a primary database?

Technically yes, but it is strongly discouraged. etcd is optimized for small configuration values (typically under 1MB each) with high read throughput. Using etcd as a primary database for application data leads to performance degradation, excessive storage growth, and unreliable operation under heavy write loads. Use TiKV or DragonflyDB for primary data storage and reserve etcd for configuration, service discovery, and distributed coordination.

### What happens when a TiKV node fails?

TiKV uses Raft consensus with typically 3 replicas per Region. When a node fails, the Raft leader election promotes a follower to leader within seconds, maintaining data availability. The Placement Driver detects the failed node and schedules new replicas on surviving nodes to restore the replication factor. Data is not lost as long as fewer than half the replicas in a Raft group fail simultaneously.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Distributed Key-Value Stores: TiKV vs DragonflyDB vs etcd",
  "description": "Compare TiKV, DragonflyDB, and etcd for self-hosted distributed key-value storage with Docker deployment guides and performance analysis.",
  "datePublished": "2026-05-17",
  "dateModified": "2026-05-17",
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
