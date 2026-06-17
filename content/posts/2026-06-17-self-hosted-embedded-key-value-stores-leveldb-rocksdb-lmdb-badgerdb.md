---
title: "Self-Hosted Embedded Key-Value Stores: LevelDB vs RocksDB vs LMDB vs BadgerDB"
date: "2026-06-17"
tags: ["database", "key-value-store", "self-hosted", "leveldb", "rocksdb", "lmdb", "badgerdb", "embedded", "opensource"]
draft: false
---

## Introduction

Not every application needs a full relational database. For many workloads — caching layers, message queues, blockchain nodes, and metadata storage — embedded key-value stores provide blazing-fast performance with minimal operational overhead. These databases run inside your application process, eliminating network round-trips and complex cluster management.

In this guide, we compare four leading open-source embedded key-value stores: **LevelDB** (Google's foundational LSM-tree engine), **RocksDB** (Facebook's high-performance fork), **LMDB** (Symas's memory-mapped B-tree database), and **BadgerDB** (Dgraph Labs' Go-native LSM store).

## Comparison Table

| Feature | LevelDB | RocksDB | LMDB | BadgerDB |
|---------|---------|---------|------|----------|
| **Data Structure** | LSM-tree | LSM-tree (optimized) | B+tree (copy-on-write) | LSM-tree (Go-native) |
| **Write Performance** | Good | Excellent (optimized for SSD) | Good (MVCC) | Excellent |
| **Read Performance** | Good | Very Good (bloom filters) | Excellent (memory-mapped) | Very Good |
| **Compression** | Snappy | Snappy, Zlib, LZ4, ZSTD | None (application-level) | Snappy, ZSTD |
| **Transactions** | Batched writes | Batched writes, snapshots | Full ACID (MVCC) | Serializable snapshot isolation |
| **Concurrency** | Single writer | Multi-threaded compaction | Multi-reader, single-writer (MVCC) | Multi-reader, single-writer |
| **GitHub Stars** | ~37,000 | ~28,000 | ~8,000 | ~14,000 |
| **Language** | C++ | C++ | C | Go |
| **License** | BSD 3-Clause | Apache 2.0 / GPLv2 | OpenLDAP | Apache 2.0 |

## LevelDB: The Foundation

LevelDB, created by Google engineers Jeffrey Dean and Sanjay Ghemawat, established the LSM-tree (Log-Structured Merge-tree) pattern that inspired an entire generation of storage engines. It writes data to an in-memory memtable, flushes to sorted SST files on disk, and periodically compacts files to reclaim space:

```cpp
#include <leveldb/db.h>

leveldb::DB* db;
leveldb::Options options;
options.create_if_missing = true;
leveldb::Status status = leveldb::DB::Open(options, "/data/leveldb", &db);

// Write
status = db->Put(leveldb::WriteOptions(), "user:1001:email", "alice@example.com");

// Read
std::string value;
status = db->Get(leveldb::ReadOptions(), "user:1001:email", &value);

// Iterate range
leveldb::Iterator* it = db->NewIterator(leveldb::ReadOptions());
for (it->Seek("user:"); it->Valid() && it->key().starts_with("user:"); it->Next()) {
    std::cout << it->key().ToString() << ": " << it->value().ToString();
}
delete it;
delete db;
```

LevelDB's simplicity is its strength — the codebase is small enough to fully understand, making it ideal for learning database internals and for use cases that don't need advanced features.

### Docker-Compose for LevelDB-Backed Services

```yaml
version: '3.8'
services:
  leveldb-api:
    image: node:18-alpine
    container_name: leveldb-service
    ports:
      - "3000:3000"
    volumes:
      - leveldb_data:/data
      - ./server.js:/app/server.js
    working_dir: /app
    command: node server.js

volumes:
  leveldb_data:
```

## RocksDB: The Performance Powerhouse

RocksDB, originally forked from LevelDB by Facebook, adds numerous optimizations for modern hardware — especially SSDs. Key enhancements include multi-threaded compaction, bloom filters for point lookups, column families for logical partitioning, and merge operators for efficient counter updates:

```cpp
#include <rocksdb/db.h>

rocksdb::DB* db;
rocksdb::Options options;
options.create_if_missing = true;
options.compression = rocksdb::kZSTD;
options.write_buffer_size = 64 * 1024 * 1024; // 64MB
options.max_write_buffer_number = 3;

// Column families for logical partitioning
rocksdb::ColumnFamilyHandle* cf_users;
rocksdb::DB::Open(options, "/data/rocksdb", {"default", "users"}, {&db, &cf_users});

// Write with merge operator for counters
db->Merge(rocksdb::WriteOptions(), cf_users, "user:1001:clicks", "1");

// Snapshot read
const rocksdb::Snapshot* snapshot = db->GetSnapshot();
rocksdb::ReadOptions read_opts;
read_opts.snapshot = snapshot;
db->Get(read_opts, cf_users, "user:1001:clicks", &value);
db->ReleaseSnapshot(snapshot);
```

RocksDB powers many production systems you already use: MySQL (MyRocks), Apache Kafka (Kafka Streams), CockroachDB, TiDB, and Apache Flink all use RocksDB as their storage engine.

## LMDB: Memory-Mapped Simplicity

LMDB (Lightning Memory-Mapped Database) takes a fundamentally different approach — instead of LSM-trees, it uses a copy-on-write B+tree fully mapped into memory. This means reads are essentially pointer dereferences into the OS page cache, making them extremely fast:

```c
#include <lmdb.h>

MDB_env *env;
MDB_dbi dbi;
MDB_txn *txn;
MDB_val key, data;

mdb_env_create(&env);
mdb_env_set_mapsize(env, 1024 * 1024 * 1024); // 1GB map
mdb_env_open(env, "/data/lmdb", 0, 0664);

mdb_txn_begin(env, NULL, 0, &txn);
mdb_dbi_open(txn, NULL, 0, &dbi);

// Write
key.mv_data = "user:1001:email";
key.mv_size = strlen(key.mv_data);
data.mv_data = "alice@example.com";
data.mv_size = strlen(data.mv_data);
mdb_put(txn, dbi, &key, &data, 0);

mdb_txn_commit(txn);

// Read (no locks needed for reads in default mode)
mdb_txn_begin(env, NULL, MDB_RDONLY, &txn);
mdb_get(txn, dbi, &key, &data);
printf("Value: %.*s\n", (int)data.mv_size, (char*)data.mv_data);
mdb_txn_abort(txn);
```

LMDB's key advantage is ACID transactions with full serializability — something LSM-tree databases struggle with. This makes it ideal for financial systems, configuration stores, and any workload requiring strict consistency.

## BadgerDB: Go-Native Performance

BadgerDB is Dgraph Labs' answer to RocksDB, written entirely in Go. It provides the performance characteristics of LSM-tree engines without CGO dependencies, making deployment simple for Go applications:

```go
package main

import (
    "github.com/dgraph-io/badger/v4"
    "log"
)

func main() {
    opts := badger.DefaultOptions("/data/badger")
    opts.Compression = badger.ZSTD
    db, err := badger.Open(opts)
    if err != nil {
        log.Fatal(err)
    }
    defer db.Close()

    // Write transaction
    err = db.Update(func(txn *badger.Txn) error {
        return txn.Set([]byte("user:1001:email"), []byte("alice@example.com"))
    })

    // Read
    err = db.View(func(txn *badger.Txn) error {
        item, err := txn.Get([]byte("user:1001:email"))
        if err != nil {
            return err
        }
        return item.Value(func(val []byte) error {
            log.Printf("Value: %s", val)
            return nil
        })
    })

    // Iterate with prefix
    db.View(func(txn *badger.Txn) error {
        it := txn.NewIterator(badger.DefaultIteratorOptions)
        defer it.Close()
        prefix := []byte("user:")
        for it.Seek(prefix); it.ValidForPrefix(prefix); it.Next() {
            item := it.Item()
            log.Printf("Key: %s", item.Key())
        }
        return nil
    })

    // Run garbage collection
    db.RunValueLogGC(0.5)
}
```

BadgerDB shines in the Go ecosystem, powering Dgraph (graph database), IPFS implementations, and various blockchain projects. Its garbage collection and value log separation give it an edge for write-heavy workloads.

## Choosing the Right Embedded Store

- **Choose LevelDB** for learning, simple embedded storage needs, and when you want a minimal, understandable codebase. It's the reference implementation that spawned an entire category.

- **Choose RocksDB** when you need maximum performance on SSD hardware, advanced features like column families and merge operators, or when deploying within an existing ecosystem that uses RocksDB (Kafka Streams, MySQL MyRocks, CockroachDB).

- **Choose LMDB** for read-heavy workloads requiring full ACID transactions, or when you need a tiny footprint with zero dependencies. Its memory-mapped approach eliminates buffer management overhead entirely.

- **Choose BadgerDB** for Go-native projects, write-heavy workloads requiring efficient garbage collection, or when you want LSM-tree performance without CGO complexity.

## Why Self-Host Embedded Databases

Embedded databases remove the operational complexity of running separate database servers. They run in-process, meaning no network configuration, no authentication management, and no separate backup procedures — your application's file backup covers the database too. For IoT devices, edge computing, and single-server applications, embedded stores dramatically reduce the attack surface.

For related self-hosted database infrastructure, see our guide on [self-hosted time-series databases](../2026-04-27-greptimedb-vs-influxdb-vs-victoriametrics-self-hosted-time-series-database-guide-2026/) and our comparison of [self-hosted graph databases](../self-hosted-graph-databases-neo4j-arangodb-nebulagraph-guide-2026/). If you need a full database server deployment, check our guide on [PostgreSQL high availability configurations](../2026-05-21-self-hosted-postgresql-ha-kubernetes-stolon-spilo-patroni-guide/).

The performance benefits are significant: embedded stores can achieve sub-millisecond reads by avoiding network round-trips entirely. For latency-sensitive applications like ad serving, real-time bidding, or API rate limiting, this makes the difference between acceptable and unacceptable performance.


## Performance Benchmarks and Practical Considerations

In production deployments, the choice between these embedded stores often comes down to specific workload patterns. RocksDB on NVMe SSDs can sustain over 500,000 random writes per second with proper tuning (64MB write buffer, 3 max write buffers, LZ4 compression). LevelDB on the same hardware typically peaks around 100,000 writes per second due to single-threaded compaction.

LMDB excels at read-heavy workloads, achieving over 1 million random reads per second when the working set fits in RAM — the memory-mapped architecture eliminates all buffer copy overhead. However, LMDB write throughput drops significantly with large transactions, as the copy-on-write B-tree must duplicate entire pages even for small modifications.

BadgerDB bridges the gap, offering RocksDB-class write performance without C++ dependencies. Its value log separation means compactions only reorganize keys, not values, reducing write amplification by 40-60% compared to traditional LSM-tree designs. For Go microservices handling mixed read-write workloads at scale, BadgerDB often provides the best balance of performance and operational simplicity.


## FAQ

### Can I use RocksDB as a replacement for Redis in production?

Not directly. RocksDB is an embedded storage engine, not a network-accessible server. You would need to build or use a server wrapper around it. Projects like Redis-on-Flash, TiKV, and ArangoDB use RocksDB internally, but they add networking, clustering, and protocol layers on top. For simple key-value cache use cases, consider using Redis or Dragonfly instead.

### How do embedded databases handle crashes and data corruption?

LSM-tree databases (LevelDB, RocksDB, BadgerDB) write sequentially to a write-ahead log (WAL) before modifying the memtable. On crash recovery, they replay the WAL. LMDB uses copy-on-write MVCC, where committed data is never overwritten in-place. All four databases are designed to survive process crashes without data loss, provided fsync is properly configured.

### What is the maximum dataset size for LMDB?

LMDB maps the entire dataset into virtual memory, so the map size must be set at environment creation time. On 64-bit systems, this can be terabytes. The practical limit depends on available virtual address space and RAM — if your working set exceeds RAM, performance degrades to disk speed, negating the memory-mapped advantage.

### Can I run multiple processes against the same embedded database?

LMDB supports multiple concurrent readers (including from separate processes) using memory-mapped files. LevelDB and RocksDB allow multiple readers but require an external lock for writing. BadgerDB is designed for single-process access. For multi-process scenarios, consider using a client-server database or implementing an access daemon.

### How do I back up an embedded database?

Since embedded databases store data as files on disk, standard file backup tools work. However, you should ensure consistency: LevelDB and RocksDB support live backups via `Checkpoint` or `GetLiveFiles`. LMDB supports hot backups via `mdb_copy`. BadgerDB provides a `Backup` API. For production deployments, combine file-level snapshots with the database's native backup API for consistent backups.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Embedded Key-Value Stores: LevelDB vs RocksDB vs LMDB vs BadgerDB",
  "description": "Compare open-source embedded key-value stores LevelDB, RocksDB, LMDB, and BadgerDB for self-hosted applications. Includes code examples, performance characteristics, and deployment guidance.",
  "datePublished": "2026-06-17",
  "dateModified": "2026-06-17",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
