---
title: "Self-Hosted Concurrent Hash Map Libraries: Dashmap vs Flurry vs Evmap vs Folly AtomicHashMap"
date: "2026-06-19"
tags: ["concurrent-data-structures", "hash-map", "rust-libraries", "cpp-libraries", "performance", "thread-safety"]
draft: false
---

Modern multi-threaded applications demand data structures that scale across CPU cores without bottlenecks. A standard `HashMap` wrapped in a mutex becomes a serialization point — only one thread can access the map at a time, killing performance under contention. Concurrent hash map libraries solve this by allowing multiple threads to read and write simultaneously using lock-free algorithms, fine-grained locking, or sharding.

This article compares four production-grade concurrent hash map implementations across Rust and C++: **Dashmap**, **Flurry**, **Evmap**, and **Folly AtomicHashMap**. Each takes a fundamentally different approach to the concurrency problem — from striped sharding to lock-free atomic operations to eventual consistency.

## Why Concurrent Hash Maps Matter

In single-threaded code, a standard `HashMap` works perfectly. But in modern server applications — web servers, database engines, message brokers, real-time analytics — multiple threads need concurrent access to shared state. A plain `Mutex<HashMap>` serializes all access: even 16 cores become effectively one when they all wait for the same lock.

Concurrent hash maps address this through several strategies:
- **Sharding**: Split the map into N independent segments, each with its own lock. Contention only occurs when two threads hit the same shard.
- **Lock-free algorithms**: Use atomic compare-and-swap (CAS) operations instead of locks, allowing threads to make progress even when others are paused.
- **Read-optimized designs**: Allow unlimited concurrent reads while serializing writes, ideal for read-heavy workloads.
- **Eventually consistent maps**: Allow reads to see slightly stale data in exchange for zero-contention writes.

Choosing the right library depends on your workload's read/write ratio, key distribution, value size, and desired consistency guarantees.

## Comparison Table

| Feature | Dashmap | Flurry | Evmap | Folly AtomicHashMap |
|---------|---------|--------|-------|---------------------|
| Language | Rust | Rust | Rust | C++ |
| GitHub Stars | 4,062 | 577 | 574 | 30,423 (Folly) |
| Concurrency Model | Sharded RwLock | Lock-free (Java CHM port) | Eventually consistent | Lock-free atomic |
| Read Performance | High (lock-free reads) | Very High | Extremely High (stale OK) | High |
| Write Performance | Good (per-shard lock) | Good | Excellent | Good |
| Consistency | Strong | Strong | Eventual | Strong |
| Memory Overhead | Moderate | Low | Low (swap-backed) | Very Low |
| Iterator Support | Yes (snapshot) | Yes | Limited | No |
| Last Updated | 2026-05-17 | 2026-04-06 | 2026-06-03 | 2026-06-19 |
| License | MIT | Apache-2.0 / MIT | MIT | Apache-2.0 |

## Dashmap: Sharded RwLock for Pragmatic Concurrency

[Dashmap](https://github.com/xacrimon/dashmap) is the most popular concurrent hash map in the Rust ecosystem, with over 4,000 stars. It implements a straightforward but effective design: the hash map is divided into `n` shards (default: number of CPUs × 4), each protected by its own `RwLock`. Hash the key, find the shard, acquire the appropriate lock.

```rust
use dashmap::DashMap;

let map = DashMap::new();
map.insert("key1", "value1");
map.insert("key2", "value2");

// Concurrent access from multiple threads
let map = std::sync::Arc::new(map);
for i in 0..4 {
    let map = map.clone();
    std::thread::spawn(move || {
        map.insert(format!("thread-{}", i), i);
        if let Some(val) = map.get("key1") {
            println!("Thread {} read: {}", i, *val);
        }
    });
}
```

Dashmap provides a familiar `HashMap`-like API with methods like `insert`, `get`, `remove`, `alter`, and `entry`. It supports both owned and reference access patterns. The `get` method returns a `Ref` that holds an `RwLock` read guard, ensuring the value cannot be modified while you hold the reference.

**Key strengths**: Drop-in replacement for `HashMap`, familiar API, lock-free reads via sharded RwLock, excellent ecosystem compatibility (works with Serde, Rayon, etc.).

**Limitations**: Write-heavy workloads can still experience contention on hot shards. The shard count is fixed at initialization and cannot grow dynamically.

## Flurry: Java's ConcurrentHashMap Ported to Rust

[Flurry](https://github.com/jonhoo/flurry) is a direct port of Java's `java.util.concurrent.HashMap` to Rust, using the same lock-free striped design. Instead of `RwLock` per shard, Flurry uses atomic operations on hash buckets, allowing true lock-free reads and fine-grained locking on writes.

```rust
use flurry::HashMap;

let map = HashMap::new();
let guard = map.guard();

map.insert("user:1001", "active", &guard);
map.insert("user:1002", "idle", &guard);

// Lock-free read — no lock acquisition at all
if let Some(status) = map.get(&"user:1001", &guard) {
    println!("User status: {}", status);
}

// Concurrent update with atomic compute
map.compute_if_present(&"user:1001", |_, val| Some(format!("{}-updated", val)), &guard);
```

The `guard` parameter is Flurry's epoch-based memory reclamation mechanism (similar to crossbeam-epoch). It ensures that memory is not freed while any thread might still be accessing it, enabling safe lock-free reads.

**Key strengths**: Proven design (Java's ConcurrentHashMap has 20+ years of production use), true lock-free reads, excellent scalability under read-heavy workloads, well-tested corner cases (resizing during concurrent access).

**Limitations**: The `guard` parameter adds API complexity compared to Dashmap. Fewer ecosystem integrations. Lower star count means a smaller community for support.

## Evmap: Eventually Consistent Multi-Value Map

[Evmap](https://github.com/jonhoo/evmap) takes a radically different approach: instead of synchronizing access to a single map, it maintains two complete copies of the data. Writers modify the "write" copy while readers access the "read" copy. A `refresh()` operation atomically swaps the two copies.

```rust
use evmap::{ReadHandle, WriteHandle};

let (reader, mut writer) = evmap::new();

// Writer thread
writer.insert("sensor-1", 42.5);
writer.insert("sensor-1", 43.1); // multi-value — both values stored
writer.refresh(); // atomically publish changes

// Reader thread — zero contention, no locks ever
if let Some(values) = reader.get_and("sensor-1", |vals| vals.iter().copied().collect::<Vec<_>>()) {
    for val in &values {
        println!("Sensor reading: {}", val);
    }
}
```

This design eliminates all contention between readers and writers: readers never block, writers never wait for readers. The trade-off is eventual consistency — readers see the last `refresh()` snapshot, not the latest individual write.

**Key strengths**: Zero read-write contention, perfect for metrics collection and real-time dashboards, multi-value support (each key can hold multiple values), extremely predictable read latency.

**Limitations**: Not suitable for workloads requiring strong consistency on every operation. Memory usage doubles (two full copies). `refresh()` is an O(n) operation that copies all pending changes. Only one writer at a time.

## Folly AtomicHashMap: Facebook's Lock-Free Powerhouse

[Folly](https://github.com/facebook/folly) is Facebook's open-source C++ library, and its `AtomicHashMap` is battle-tested in production at massive scale. It uses a lock-free open-addressing design with atomic operations for all reads and writes.

```cpp
#include <folly/AtomicHashMap.h>

// Pre-allocate capacity — no dynamic resizing
folly::AtomicHashMap<uint64_t, std::string> map(1024 * 1024);

// Lock-free insert
auto result = map.insert(42, "the answer");
if (result.second) {
    std::cout << "Inserted successfully" << std::endl;
}

// Lock-free find
auto it = map.find(42);
if (it != map.end()) {
    std::cout << "Found: " << it->second << std::endl;
}
```

Folly's AtomicHashMap pre-allocates its entire capacity upfront and never resizes. This eliminates the complex lock-free resizing problem entirely. The map uses open addressing with quadratic probing and atomic compare-and-swap for all operations.

**Key strengths**: Proven at Facebook scale (billions of operations per second), extremely low memory overhead (flat array, no per-node allocation), predictable latency (no resizing pauses), comprehensive C++ integration (works with Folly's fiber, future, and executor frameworks).

**Limitations**: Fixed capacity — must know maximum size upfront or risk insertion failure. C++ only. Part of a large library (Folly) which adds build complexity. No iterator support (by design, to avoid ABA problems).

## Choosing the Right Concurrent Hash Map

The choice depends heavily on your workload characteristics:

- **For general Rust applications**: Start with **Dashmap**. Its sharded RwLock design is familiar, safe, and handles most workloads well. The drop-in `HashMap` replacement API means minimal code changes.

- **For read-heavy Rust workloads**: Consider **Flurry**. Its lock-free reads scale better than sharded RwLock when reads dominate (>90% read ratio). The API is slightly more complex but the performance gains can be significant.

- **For metrics and monitoring**: **Evmap** shines with its zero-contention design. If you're collecting metrics from multiple threads and displaying them in a dashboard, the eventual consistency model is perfect — a 100ms delay in seeing new data is irrelevant.

- **For C++ high-performance systems**: **Folly AtomicHashMap** is the gold standard when you know your capacity bounds. It's been running Facebook's infrastructure for years and handles extreme throughput.

## Implementation Considerations

When integrating a concurrent hash map into your application, watch for these common pitfalls:

**1. Key Distribution**: All concurrent maps rely on good hash distribution. A poor hash function that maps many keys to the same bucket will create hotspots regardless of the concurrency model. Use a quality hash function (Rust's default `RandomState` with SipHash, or Folly's `folly::Hash`).

**2. Resize Strategy**: Understand when and how your chosen map resizes. Dashmap and Flurry resize automatically but may pause briefly during expansion. Evmap doubles memory periodically during `refresh()`. Folly AtomicHashMap simply doesn't resize — inserts fail when full.

**3. Iteration Semantics**: Iterating a concurrent map while other threads are modifying it requires careful thought. Dashmap provides atomic snapshots. Flurry offers guarded iteration. Evmap provides read-only iteration of the published snapshot. Folly AHM intentionally omits iteration.

**4. Value Semantics**: Consider what "consistency" means for your values. If you're storing complex objects (not just primitives), a concurrent map protects the map structure but not the values themselves. Use atomic types or additional synchronization for value-level atomicity.

## Performance Characteristics

Under a typical mixed workload (80% reads, 20% writes) with 8 threads, these libraries exhibit different performance profiles:

- **Evmap** achieves near-linear read scaling because reads never touch any shared state. Write throughput is limited by the single writer and `refresh()` cost.

- **Dashmap** shows excellent read scaling (sharded RwLock allows multiple concurrent reads) but writes contend on the per-shard lock.

- **Flurry** demonstrates the best balanced performance with lock-free reads and efficient write locking, closely matching Java's ConcurrentHashMap behavior.

- **Folly AtomicHashMap** provides the lowest per-operation latency but requires pre-allocation and operates in C++.

For related reading on concurrent data structure design, see our [lock-free concurrent data structures guide](../2026-06-19-lockfree-concurrent-data-structures-crossbeam-disruptor-folly-ck/) and [probabilistic data structures comparison](../2026-06-19-probabilistic-data-structures-bloom-cuckoo-hyperloglog-countmin/). If you're optimizing memory allocation alongside concurrency, our [memory allocators guide](../2026-06-02-memory-allocators-jemalloc-tcmalloc-mimalloc-guide/) covers complementary performance improvements.

## FAQ

### When should I use a concurrent hash map instead of Mutex<HashMap>?

Switch when profiling shows the mutex is a bottleneck. Under low contention (< 2 threads), `Mutex<HashMap>` is usually faster because it avoids the overhead of sharding or lock-free algorithms. Measure first — don't prematurely optimize. A good heuristic: if your per-operation time exceeds 1 microsecond under `Mutex<HashMap>`, try Dashmap or Flurry.

### Is Dashmap always safe to use as a drop-in replacement for HashMap?

Almost always. Dashmap implements most of HashMap's API surface, but there are differences: `get` returns a `Ref` rather than `&V`, the entry API works slightly differently, and iteration requires special handling. If your code uses only `insert`, `get`, `remove`, and `contains_key`, the migration is seamless. For advanced patterns like `entry().or_insert()`, check the Dashmap documentation for the equivalent `alter()` or `entry()` API.

### What's the difference between Evmap's eventual consistency and a regular HashMap?

Evmap maintains two complete copies of the data. Writers modify the "hidden" copy and call `refresh()` to atomically swap. Between `refresh()` calls, readers see the old snapshot. This means if a writer inserts a value at time T, readers may not see it until the next `refresh()` at time T+delta. For metrics dashboards or rate counters, this 10-100ms delay is usually acceptable. For financial transactions, it's not.

### Can I use Folly AtomicHashMap outside of Facebook's infrastructure?

Yes. Folly is fully open-source under Apache 2.0 and builds cleanly on Linux and macOS. The main consideration is that it's a C++17 library — if your project is in Rust, Go, or another language, you'd need FFI bindings. For C++ projects, Folly integrates via CMake and can be fetched as a dependency from vcpkg or built from source.

### How do these libraries compare to a simple RwLock<HashMap> in practice?

Under 1-2 threads with mostly reads, `RwLock<HashMap>` performs similarly to Dashmap — both use reader-writer locks at their core. At 4+ threads, Dashmap's sharding (default 4×CPU count shards) reduces contention significantly: instead of all threads contending for one RwLock, they spread across many. In benchmarks, Dashmap shows 3-5× higher throughput than `RwLock<HashMap>` at 8 threads with mixed read/write workloads.

### Do I need a concurrent hash map if I'm using async Rust (tokio)?

Yes and no. Tokio tasks run cooperatively on a thread pool — if a task holds a `Mutex` lock across an `.await` point, it can deadlock the entire runtime. You can use `tokio::sync::Mutex` for async-safe locking, or use a concurrent hash map like Dashmap which doesn't require holding locks across await points. For CPU-bound work within a single task, `std::sync::Mutex` is fine — it's only across `.await` boundaries that you need caution.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Concurrent Hash Map Libraries: Dashmap vs Flurry vs Evmap vs Folly AtomicHashMap",
  "description": "Comprehensive comparison of concurrent hash map libraries for Rust and C++: Dashmap, Flurry, Evmap, and Folly AtomicHashMap. Includes code examples, performance analysis, and selection guidance for multi-threaded applications.",
  "datePublished": "2026-06-19",
  "dateModified": "2026-06-19",
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
