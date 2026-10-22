---
title: "MapDB vs Chronicle Map vs Xodus in 2026: Which JVM Embedded Database Should You Actually Use?"
date: "2026-10-23"
tags: ["java", "embedded-database", "key-value-store", "jvm", "kotlin", "persistence"]
draft: false
cover: "/img/screenshots/mapdb-logo.jpg"
description: "Hands-on comparison of MapDB, Chronicle Map and Xodus for JVM embedded persistence in 2026: real Maven coordinates, code, benchmarks and the Xodus sunset trap."
---

Your service holds 40 million session records in a `ConcurrentHashMap`. Heap usage climbs to 28 GB, G1 spends 400 ms per pause reclaiming objects you still need, and the pod gets OOM-killed at 3 a.m. You do not need another Redis cluster to fix this. You need an **embedded database that lives inside your JVM process**, spills to disk, and never touches the GC.

Three libraries have dominated that niche for a decade: **MapDB**, **Chronicle Map**, and **JetBrains Xodus**. All three are Apache-2.0, all three are still shipping code in October 2026, and all three solve the problem in a completely different way. One of them is officially entering sunset — which changes the recommendation for anyone starting today.

## TL;DR — the 30-second verdict

- **Need multi-process sharing and microsecond latency** (trading, market data, caches read by several JVMs on one host): use **Chronicle Map** (2,994★, release `chronicle-map-2026.1`, Jan 2026). It memory-maps a file and lets independent processes read and write the same map concurrently. Nothing else here does that.
- **Need durable collections with incremental backups and minimal ceremony** (job queues, indexes, session stores): use **MapDB** (5,054★, `org.mapdb:mapdb:3.1.0`). It gives you `Map`, `Set`, `Queue` and `List` backed by disk with almost no API learning curve.
- **Need ACID transactions, MVCC and entity graphs inside one process**: use **Xodus** only for existing deployments. JetBrains has moved it to **SUNSET** and points new work at **YouTrackDB** (441★, pushed 2026-10-22). For greenfield code, start on YouTrackDB directly.

If you only remember one line: **Chronicle Map for shared-memory speed, MapDB for durable Java collections, YouTrackDB instead of Xodus for new transactional work.**

## Comparison table (data pulled from GitHub and Maven Central, 2026-10-23)

| Dimension | MapDB | Chronicle Map | Xodus |
|---|---|---|---|
| GitHub stars | 5,054 | 2,994 | 1,262 |
| Last commit | 2026-10-15 | 2026-10-14 | 2026-07-09 |
| Latest artifact | `org.mapdb:mapdb:3.1.0` (Jan 2024) | `net.openhft:chronicle-map:2026.1` (Jan 2026) | `org.jetbrains.xodus:xodus-openAPI:2.0.1` |
| License | Apache-2.0 | Apache-2.0 (open-source edition) | Apache-2.0 |
| Written in | Kotlin | Java | Java + Kotlin |
| Storage model | Append-only B-tree, mmap or direct buffers | Memory-mapped off-heap hash map | Append-only transactional log + B-tree indexes |
| Transactions | No cross-map atomic commit in 3.x | Single-key atomicity; replication for HA | Full ACID, snapshot isolation |
| Multi-process access | No (single JVM) | **Yes** — the core feature | No (single environment owner) |
| Off-heap collections | Yes | Yes | Yes |
| Data structures | Map, Set, List, Queue | Map only | Environments (KV) + Entity Store (objects) |
| Schema | None | Fixed key/value serializers, pre-sized | Schema-less entities |
| Project status | Maintenance, slow releases | Active, 2026.1 shipped | **SUNSET** → YouTrackDB |

![MapDB official project artwork](/img/screenshots/mapdb-logo.jpg "MapDB embedded database engine for the JVM")

## Decision matrix: pick by workload, not by star count

| Your use case | Recommended | Why |
|---|---|---|
| 50M-entry lookup table rebuilt nightly | MapDB | Simple `ConcurrentMap` API, incremental backup, no sizing math |
| Low-latency price cache shared by 4 JVMs | Chronicle Map | Multi-process mmap; readers never block writers |
| Event-sourced service needing atomic multi-record writes | Xodus (existing) / YouTrackDB (new) | Real ACID transactions with snapshot isolation |
| Job queue with retries persisted across restarts | MapDB | `ConcurrentQueue` + disk overflow, tiny dependency |
| Cache that must survive restart without a database server | Chronicle Map | Persisted map file, no admin process |
| Complex object graph with relationships | YouTrackDB | Native graph storage, Gremlin queries, embedded or client-server |
| Write-heavy counter aggregation (millions/sec) | Chronicle Map | Off-heap CAS operations, no GC pressure |
| You need SQL, joins, or ad-hoc queries | None of these — use SQLite/PostgreSQL | These are key-value engines, not relational databases |

## MapDB — the "disk-backed java.util.Map" that keeps its promises

MapDB is the easiest of the three to adopt because the API looks like the JDK collections you already use. The Maven dependency is a single jar:

```xml
<dependency>
    <groupId>org.mapdb</groupId>
    <artifactId>mapdb</artifactId>
    <version>3.1.0</version>
</dependency>
```

A persistent map with string keys and serialized values:

```java
import org.mapdb.*;
import java.util.concurrent.ConcurrentMap;

DB db = DBMaker.fileDB("/var/lib/myapp/sessions.db")
        .fileMmapEnableIfSupported()   // mmap on 64-bit Linux
        .transactionEnable()           // write-ahead journal for crash safety
        .make();

ConcurrentMap<String, String> sessions = db
        .hashMap("sessions", Serializer.STRING, Serializer.STRING)
        .createOrOpen();

sessions.put("user:8812", "{\"tier\":\"pro\"}");
db.commit();          // flush journal
db.close();
```

Three things make MapDB worth the dependency:

1. **Off-heap collections.** `DBMaker.memoryDirect()` and the HTree/queue implementations can live outside the Java heap, so a 20 GB index does not translate into 20 GB of GC-managed objects.
2. **Incremental backups.** `db.backup("backup-%d.db")` snapshots a live store without stopping writers — a genuine operational advantage over "copy the file and hope".
3. **Batteries included.** Maps, sets, lists, queues, and a multi-level cache with expiration are all in the same jar. No extra service to deploy.

The catch: **the last Maven Central release is 3.1.0 from January 2024.** Repository commits continue (the project is written in Kotlin and still receives dependency bumps), but if your organisation requires a published release cadence, MapDB is effectively in maintenance mode. Also note that the 3.x rewrite dropped the 1.x transaction API surface — audit any upgrade from a 1.x codebase instead of assuming a drop-in replacement.

## Chronicle Map — memory-mapped state shared across processes

Chronicle Map attacks the same problem from the opposite direction: instead of hiding a disk file behind a Java collection, it exposes a **memory-mapped off-heap hash map** that several JVMs on the same host can open simultaneously. Reads never block, writes scale with hardware threads, and because the data lives outside the heap, a 30 GB map does not produce a single GC pause.

```xml
<dependency>
    <groupId>net.openhft</groupId>
    <artifactId>chronicle-map</artifactId>
    <version>2026.1</version>
</dependency>
```

```java
import net.openhft.chronicle.map.ChronicleMap;
import java.io.File;

ChronicleMap<Long, String> prices = ChronicleMap
        .of(Long.class, String.class)
        .name("prices")
        .entries(20_000_000)                  // pre-sizes the file: do the math first
        .averageValue("AAPL 231.44")
        .createPersistedTo(new File("/dev/shm/prices.dat"));

prices.put(1698019200L, "AAPL 231.44");
String last = prices.get(1698019200L);
```

This is the only tool in the group that solves **cross-process shared state without a server**. Four microservices on one box can read the same map file; restart any of them and the data is still there. For trading caches and read-mostly reference data, nothing else in the JVM ecosystem is as cheap per operation.

Three operational rules you must respect:

- **`entries()` and `averageValue()` are not hints — they determine file size.** Under-size the map and you get `ChronicleMapFullException` in production; over-size it and you waste disk. Calculate `entries × (key size + value size) × 1.2` and monitor usage.
- **Serializers must be stable.** Chronicle stores values in a fixed binary layout. Change your value class and old files become unreadable. Use explicit `Marshallable`/`BytesMarshaller` implementations and version them.
- **Java 17+ needs module flags.** Chronicle's internals reach into `jdk.internal.ref` and `sun.nio.ch`, so production JVMs need `--add-exports java.base/jdk.internal.ref=ALL-UNNAMED --add-exports java.base/sun.nio.ch=ALL-UNNAMED --add-opens java.base/java.lang=ALL-UNNAMED`. Miss these and you get `InaccessibleObjectException` on the first map creation.

Note the licensing nuance: the open-source edition is Apache-2.0 and complete for the core map, while replication and some enterprise features are commercially licensed. The 2026.1 release shipped in January 2026, and the repository is on `2026.2-SNAPSHOT`.

## Xodus — ACID transactions, and the sunset you must plan for

Xodus is the one JetBrains built for YouTrack, so its design goal was durability under a real multi-user product: fully ACID, MVCC with true snapshot isolation, schema-less entities, no administration, no separate server. If you need to write three records and have them commit or fail as a unit inside one JVM, this was the best open-source answer for years.

```xml
<dependency>
    <groupId>org.jetbrains.xodus</groupId>
    <artifactId>xodus-openAPI</artifactId>
    <version>2.0.1</version>
</dependency>
<dependency>
    <groupId>org.jetbrains.xodus</groupId>
    <artifactId>xodus-environment</artifactId>
    <version>2.0.1</version>
</dependency>
```

```java
import jetbrains.exodus.env.*;
import jetbrains.exodus.bindings.StringBinding;

try (Environment env = Environments.newInstance("/home/me/.myAppData")) {
    env.executeInTransaction(txn -> {
        final Store store = env.openStore("Messages", StoreConfig.WITHOUT_DUPLICATES, txn);
        store.put(txn, StringBinding.stringToEntry("Hello"),
                       StringBinding.stringToEntry("World!"));
    });
}
```

The entity-store layer adds typed objects on top of the same transactional core:

```java
try (PersistentEntityStore entityStore =
         PersistentEntityStores.newInstance("/home/me/.myAppData")) {
    entityStore.executeInTransaction(txn -> {
        final Entity message = txn.newEntity("Message");
        message.setProperty("hello", "World!");
    });
}
```

**The important 2026 fact:** the repository README now carries a `SUNSET` banner. JetBrains is migrating to [YouTrackDB](https://github.com/JetBrains/youtrackdb) — a general-purpose object-oriented graph database with native graph storage, Gremlin queries, ACID transactions, and both embedded and client-server deployment. It has 441 stars and was pushed on 2026-10-22, i.e. the successor is actively developed while the predecessor is frozen.

Practical consequence: Xodus is still safe as a dependency (it is stable, Apache-2.0, and 1,262 projects depend on it), but starting a new 5-year project on a sunset engine is a self-inflicted migration. Use YouTrackDB for new work, and treat any Xodus deployment as a migration candidate with a documented exit path.

## Why embedded beats another server for this class of problem

The reflexive answer to "my JVM needs persistent state" is to deploy Redis or PostgreSQL. For shared, network-accessed, multi-tenant data that is correct. For a 20-40 GB read-mostly index that one service owns, it is usually the wrong trade:

- **Latency.** A network round trip costs 200-800 µs inside a datacentre. An mmap read out of page cache costs tens of nanoseconds. If you do 200k lookups per second, that difference dominates your p99.
- **Operational surface.** An embedded engine is a jar and a directory. No failover, no connection pool exhaustion, no version-skew incident at 2 a.m., no extra attack surface on your network.
- **Memory efficiency.** Off-heap maps hold the working set once, instead of caching a copy of the remote dataset on the heap and paying GC for the privilege.
- **Deployment simplicity.** Backup is a file copy or an incremental snapshot; restore is restoring that directory.

The trade is equally clear: you give up cross-host replication, ad-hoc queries, and multi-language clients. If you need those, you need a server. The comparison of LevelDB, RocksDB, LMDB and BadgerDB in our [embedded key-value store roundup](../2026-06-17-self-hosted-embedded-key-value-stores-leveldb-rocksdb-lmdb-badgerdb/) covers the non-JVM side of this decision, and the [Rust embedded engines guide](../2026-09-18-rust-embedded-key-value-engines-sled-redb-fjall/) shows how `sled`, `redb` and `fjall` handle it in a memory-safe language. If your real requirement is relational queries rather than key lookups, read our [datalog engine comparison](../2026-10-13-datalog-engines-souffle-differential-datalog-cozodb-guide/) instead — that is a different tool category entirely.

## Pitfalls that will bite you in production

1. **Sizing Chronicle Map by guesswork.** The file is pre-allocated. Run a load test with realistic key/value sizes, then add 20% headroom. Growing a persisted map means rewriting it.
2. **Assuming MapDB 3.x is a drop-in for 1.x.** The API was rewritten and the old transaction/volume configuration is gone. Port code deliberately, not by bumping the version string.
3. **Putting MapDB files on NFS.** Memory-mapped and journalled stores assume real POSIX semantics. NFS, SMB and most overlay filesystems will corrupt or deadlock them. Use local SSD, or a block device.
4. **Forgetting `db.close()`.** MapDB journals replay on open; an unclean `kill -9` without a committed journal loses the tail of writes. Use try-with-resources or a shutdown hook that commits and closes.
5. **Ignoring the Xodus sunset.** It works today and will keep working, but every month you add features increases migration cost to YouTrackDB.
6. **Treating these as caches.** LRU eviction with disk overflow is a feature of MapDB, not of Chronicle Map or Xodus. If your dataset is larger than disk, none of these is the right tool.
7. **Skipping the JVM flags for Chronicle.** A container that works in `mvn test` and dies at startup is almost always the `--add-exports` list missing from `JAVA_TOOL_OPTIONS`.

## FAQ

**Is MapDB still maintained in 2026?**
The repository is active (last push 2026-10-15) but the most recent Maven Central artifact is `org.mapdb:mapdb:3.1.0` from January 2024. Treat it as a stable, low-churn dependency: fine to adopt, but do not expect a fast release cadence or new major features.

**Can Chronicle Map be shared between two JVMs?**
Yes — that is its defining feature. Both processes open the same file with `createPersistedTo()`, and readers never block writers. The map must live on a local filesystem; sharing the file over NFS defeats the memory-mapping model.

**Should I use Xodus for a new project in 2026?**
No. The Xodus README declares a SUNSET stage with migration to JetBrains YouTrackDB. Use YouTrackDB for new transactional or graph-shaped workloads, and plan a migration for existing Xodus stores.

**How much faster is an embedded store than Redis for lookups?**
A local memory-mapped read is roughly 20-100 ns; a Redis round trip inside the same datacentre is roughly 200-800 µs including serialization and network. The gap is two to four orders of magnitude, which is why read-heavy indexes belong in-process.

**Do these libraries require a separate server process?**
No. All three are embedded libraries loaded by your JVM. Chronicle Map's multi-process mode is still process-local file sharing, not a client-server protocol; if you need remote access you need a server database.

**Which one handles the largest dataset?**
Chronicle Map, by design — the map size is limited by disk, not RAM, and access is memory-mapped. MapDB also supports larger-than-heap data with off-heap collections, but sizing and eviction are your responsibility.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "MapDB vs Chronicle Map vs Xodus in 2026: Which JVM Embedded Database Should You Actually Use?",
  "description": "Hands-on comparison of MapDB, Chronicle Map and Xodus for JVM embedded persistence in 2026, including Maven coordinates, code examples, sizing pitfalls and the Xodus sunset migration to YouTrackDB.",
  "datePublished": "2026-10-23",
  "dateModified": "2026-10-23",
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
