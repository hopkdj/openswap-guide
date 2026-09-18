---
title: "Sled vs Redb vs Fjall in 2026: Which Rust Embedded Key-Value Engine Should You Actually Ship?"
date: 2026-09-18
tags: ["rust", "embedded-database", "key-value-store", "storage-engine"]
draft: false
cover: "/img/screenshots/rust-kv-fjall-logo.jpg"
---

Every Rust service eventually slams into the same wall: you need a durable key-value store *inside* the process, and spinning up PostgreSQL just to hold 40 GB of index data feels absurd. You want `open()`, `insert()`, `get()`, and a promise that a `kill -9` will not shred your data. Three pure-Rust engines dominate that niche in 2026 — **sled, redb, and fjall** — and picking the wrong one costs you a rewrite, because their on-disk formats, transaction semantics, and concurrency models are not interchangeable.

This is the practical comparison: what each engine actually guarantees, the code that gets you running in five minutes, and the production traps that the READMEs gloss over.

## TL;DR: Quick Verdict

**If you want correctness with the smallest API surface, pick redb.** It gives you real ACID transactions, a single portable file, zero-copy reads, and typed tables — with no beta warnings.

**If you need lock-free atomic operations and change subscriptions, pick sled** — but go in knowing its on-disk format is explicitly not stable across releases, so treat it as data you can rebuild from source-of-truth storage.

**If you are ingesting hundreds of gigabytes on a write-heavy workload, pick fjall.** Log-structured compaction, keyspace partitioning, and optional blob separation were designed for exactly that shape.

**If you need multiple processes hitting the same data, or replication, none of these are the answer** — reach for TiKV, FoundationDB, or etcd instead.

## How the Three Engines Differ Under the Hood

| Dimension | sled | redb | fjall |
|---|---|---|---|
| Latest release (2026-09) | 0.34.7 | 4.3.0 | 3.1.10 |
| GitHub stars | 9,091 | 4,792 | 2,333 |
| Last upstream commit | 2026-04-04 | 2026-09-18 | 2026-09-13 |
| License | Apache-2.0 | Apache-2.0 | MIT OR Apache-2.0 |
| Core data structure | lock-free Bw-tree | copy-on-write B+tree, MVCC | log-structured merge tree |
| Transactions | per-key atomics, batch, no multi-tree ACID | full multi-table ACID + savepoints | keyspace-level, `TxKeyspace` for transactions |
| Value typing | raw bytes / `IVec` | typed `TableDefinition<K, V>` | raw bytes + typed partitions |
| Change streams | `watch_prefix` subscriptions | none built in | none built in |
| On-disk format guarantee | not stable across versions | versioned format, documented | versioned LSM format |
| Multi-process access | exclusive lock | exclusive lock | exclusive lock |
| Sweet spot | embedded cache + reactive invalidation | embeddable transactional DB | write-heavy large datasets |

The table already tells the story: this is not three implementations of the same thing. It is a **Bw-tree**, a **copy-on-write B+tree**, and an **LSM-tree** — three different answers to the read-amplification versus write-amplification trade-off.

## Decision Matrix: Pick by Use Case

| Your situation | Pick | Why |
|---|---|---|
| Local config/session store inside a web service | redb | ACID commit semantics, one file, trivial backup |
| Cache that must invalidate in-process consumers | sled | `watch_prefix` change streams, no polling loop |
| 200 GB write-heavy event or log index | fjall | LSM compaction absorbs writes; blobs can live separately |
| Data you cannot afford to lose | redb | Transactions + documented format versioning |
| Data you can rebuild from Kafka/object storage | sled | Fast, lock-free reads; format churn is acceptable |
| Multiple services sharing one store | none of these | All three take a file lock; use a network store |
| Replicated, cluster-wide consistency | none of these | Use TiKV/FoundationDB — see our [distributed key-value store guide](../2026-05-17-self-hosted-distributed-key-value-stores-tikv-dragonflydb-etcd-guide/) |

## sled: The Battle-Tested Engine That Still Says Beta

sled is the oldest and most starred of the trio — 9,091 stars — and it is still described by its own maintainer as beta. It uses a lock-free Bw-tree, which means readers never block writers and you get very cheap concurrent reads. The API is almost aggressively simple:

```rust
let tree = sled::open("/tmp/welcome-to-sled")?;

// insert and get, similar to std's BTreeMap
let old_value = tree.insert("key", "value")?;

assert_eq!(
  tree.get(&"key")?,
  Some(sled::IVec::from("value")),
);

// range queries
for kv_result in tree.range("key_1".."key_9") {}

// deletion
let old_value = tree.remove(&"key")?;

// atomic compare and swap
tree.compare_and_swap(
  "key",
  Some("current_value"),
  Some("new_value"),
)?;
```

Two things make sled genuinely different. First, `compare_and_swap` and `fetch_and_update` give you atomic read-modify-write without a transaction wrapper — ideal for counters, leases, and lock tables. Second, change subscriptions let consumers react instead of poll:

```rust
let sled = sled::open("my_db").unwrap();
let mut sub = sled.watch_prefix("");

sled.insert(b"a", b"a").unwrap();

extreme::run(async move {
    while let Some(event) = (&mut sub).await {
        println!("got event {:?}", event);
    }
});
```

**Where sled hurts:** there is no multi-tree ACID transaction, so multi-key invariants are your problem. And the project does not promise on-disk format stability across versions — a routine `cargo update` has historically required a dump-and-reload. If a store is the source of truth for anything you cannot regenerate, that is a serious constraint, not a footnote. Last upstream commit: 2026-04-04, so development has slowed compared to its peers.

## redb: ACID Transactions in a Single File

redb's design goal is the opposite of sled's: fewer moving parts, stronger guarantees. It is a copy-on-write B+tree with full MVCC, so a write transaction can commit atomically across multiple tables, and readers keep seeing a consistent snapshot while it happens. The typed table API is the nicest of the three:

```rust
use redb::{Database, Error, ReadableDatabase, TableDefinition};

const TABLE: TableDefinition<&str, u64> = TableDefinition::new("my_data");

fn main() -> Result<(), Error> {
    let db = Database::create("my_db.redb")?;
    let write_txn = db.begin_write()?;
    {
        let mut table = write_txn.open_table(TABLE)?;
        table.insert("my_key", &123)?;
    }
    write_txn.commit()?;

    let read_txn = db.begin_read()?;
    let table = read_txn.open_table(TABLE)?;
    assert_eq!(table.get("my_key")?.unwrap().value(), 123);

    Ok(())
}
```

Why teams standardize on redb:

- **One file, no directory of segments.** Backup is a file copy, which matters enormously in edge and desktop deployments.
- **Transactions with savepoints.** You can abort a nested unit of work without aborting the outer one.
- **Zero-copy reads.** Values are handed back as borrowed access guards rather than freshly allocated buffers.
- **Active maintenance.** Commits landed the same day this article was written (2026-09-18), release 4.3.0.

The cost of the model is write-path behavior: copy-on-write B+trees do more page copying on large updates than an LSM tree, and long-running read transactions hold pages that would otherwise be reclaimed. Keep read transactions short and you will not notice.

## fjall: Log-Structured Storage for Bigger Datasets

fjall (formerly known in its 2.x line as an LSM engine, now at 3.1.10) is what you pick when the dataset outgrows a page-cache-friendly B+tree. Each keyspace is its own physical LSM-tree, which means you can isolate hot and cold data and compact them independently instead of paying rewrite amplification on everything at once:

```rust
use fjall::{Database, KeyspaceCreateOptions, PersistMode};

fn main() -> fjall::Result<()> {
    // A database may contain multiple keyspaces
    // You should probably only use a single database for your application
    let db = Database::builder(path).open()?;
    // TxDatabase::builder for transactional semantics

    // Each keyspace is its own physical LSM-tree, and thus isolated from other keyspaces
    let items = db.keyspace("my_items", KeyspaceCreateOptions::default)?;

    // Write some data
    items.insert("a", "hello")?;

    // And retrieve it
    let bytes = items.get("a")?;

    // Or remove it again
    items.remove("a")?;

    // Search by prefix
    for kv in items.prefix("prefix") {
        // ...
    }
    Ok(())
}
```

The 3.x line adds what LSM engines usually lack in Rust: transactional keyspaces (`TxDatabase::builder`) for multi-key atomicity, plus partitions for range-based physical separation. If your workload is "append a lot, read by prefix or range, tolerate some read amplification," fjall fits better than either B+tree engine.

**Where fjall hurts:** compaction is a background I/O consumer. On a shared VPS with a noisy disk budget, spike-aware scheduling matters more than benchmark tables. And 2,333 stars means a smaller community and fewer battle reports than sled.

## Operational Pitfalls That Bite in Production

1. **All three take an exclusive file lock.** Two processes cannot open the same store. In containerized setups, that means a sidecar container and the main app cannot share a mounted sled, redb, or fjall directory — you will get a lock error at startup, sometimes only under restart races.
2. **Do not treat any of them as a network database.** There is no wire protocol, no authentication, no replication. Embedding a store to avoid operational overhead is smart; using it to avoid a real database for a multi-node service is not.
3. **Durability is a knob, not free.** Every `insert` that waits for an fsync costs orders of magnitude more than one that does not. Batch writes and commit once per logical operation instead of per key.
4. **Disk-full handling differs.** A copy-on-write engine can fail a write transaction cleanly; an LSM engine may stall on compaction while the same disk is nearly full. Put a hard space alarm on the volume.
5. **Format upgrades need a migration plan.** With sled especially, assume the binary format can change between minor versions. Keep a rebuildable copy elsewhere, or pin the version and own the upgrade.
6. **Value size drives the choice.** Megabyte-scale values inside an LSM tree inflate compaction badly; separate blob storage (or a purpose-built blob tree) is the standard fix.
7. **Measure with your access pattern, not a synthetic benchmark.** Sequential-key benchmarks flatter LSM engines and random-read benchmarks flatter B+tree engines; production mixes both.

## Why Rust Teams Keep the Data Layer In-Process

The pattern behind all three projects is the same: teams are moving the storage engine into the application binary. A single static binary plus one data file is deployable to a VPS, a Raspberry Pi, an edge gateway, or a customer's laptop without a database operator in the loop — no ports to expose, no credentials to rotate, no migration window at 3 a.m. For workloads that fit a single node, that is a genuinely better trade than running a database server you must then patch, monitor, and back up.

If your Rust service needs crash-safe local state, the practical sequence is: start with redb for its transactions, move to fjall once write volume or dataset size makes compaction the cheaper trade, and reach for sled when change subscriptions or atomic primitives are core to the design. When the design outgrows one process, that is the signal to graduate — see our [embedded database engine comparison](../2026-06-13-self-hosted-embedded-database-engines-libmdbx-lmdb-unqlite-vedis/) and [binary serialization frameworks guide](../2026-06-19-binary-serialization-frameworks-bincode-borsh-postcard-rkyv/) for the on-disk and encoding layers that sit underneath.

## FAQ

**Is sled still maintained in 2026?**
Yes, but slowly. The last upstream commit was 2026-04-04 and the latest release remains 0.34.7, still labeled beta. It is stable enough for cache-like workloads where you can rebuild the data, which is how most production users deploy it.

**Which Rust embedded database is fastest for reads?**
It depends on the read pattern rather than a single winner. sled's lock-free Bw-tree favors concurrent point reads, redb's MVCC snapshot design favors consistent transactional reads, and fjall's LSM tree favors prefix and range scans over recently written data. Benchmark with your own key distribution.

**Can two processes open the same redb or fjall database?**
No. Both engines take an exclusive file lock on the database document. Multi-process access requires a network database such as TiKV, FoundationDB, or PostgreSQL.

**Does redb support transactions across multiple tables?**
Yes. A write transaction can open several tables, modify all of them, and commit atomically. Redb also supports savepoints inside a transaction so you can roll back part of the work while keeping the rest.

**Do these engines have Docker images or a server mode?**
No — they are libraries compiled into your application. The right pattern is to expose your own service API over HTTP or gRPC and let the store live inside that process, with the data directory on a persistent volume.

**How do I back up an embedded store safely?**
For redb, commit or pause writes and copy the single database file. For sled and fjall, prefer an application-level snapshot or a filesystem snapshot taken while the process is stopped, since copying a directory mid-compaction can capture an inconsistent state.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Sled vs Redb vs Fjall in 2026: Which Rust Embedded Key-Value Engine Should You Actually Ship?",
  "description": "Hands-on comparison of sled, redb and fjall, the three leading pure-Rust embedded key-value engines: transactions, storage architecture, licenses, performance trade-offs and production pitfalls.",
  "datePublished": "2026-09-18",
  "dateModified": "2026-09-18",
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
