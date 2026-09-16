---
title: "Moka vs cached vs lru in 2026: Which Rust Cache Crate Should You Actually Use?"
date: "2026-09-17"
tags: ["rust", "caching", "performance", "developer-tools", "backend"]
description: "A hands-on comparison of the three most-used Rust caching crates in 2026 — moka 0.12, cached 4.0 and lru 0.18 — with real code, concurrency semantics and hit-ratio trade-offs."
draft: false
---

Your service is doing 10,000 database reads per second for the same 200 rows. You add a `HashMap`, and a week later it has grown to 40 GB and your container is being killed by the OOM reaper. That is the moment every Rust backend engineer goes shopping for a cache crate — and immediately runs into three very different designs calling themselves "a cache."

**moka**, **cached** and **lru** all solve the eviction problem, but they solve it at different layers: one is a concurrent cache engine modeled on Java's Caffeine, one is a memoization framework built around procedural macros, and one is a plain data structure that expects *you* to handle the threading. Choosing wrong costs you either a week of lock-contention debugging or a cache that silently stops working under load.

## TL;DR: The Quick Verdict

- **Pick `moka` if you have a real concurrent service.** `get` takes `&self`, so any number of reader threads proceed in parallel, and TinyLFU admission keeps hit ratios high on skewed traffic. This is the default answer for axum/actix backends.
- **Pick `cached` if what you actually want is memoization.** One attribute macro turns an expensive function into a cached one, including async functions, TTLs and sharded caches. Least code, least ceremony.
- **Pick `lru` if you need a deterministic, single-threaded LRU *data structure*** — inside a parser, a CLI tool, a request-scoped buffer — or if you want to build your own sharding on top of a minimal dependency tree.

If you only remember one line: **`moka` for shared caches, `cached` for expensive functions, `lru` for internal bookkeeping.**

## Head-to-Head Comparison (September 2026 data)

All numbers pulled live from GitHub and crates.io on 2026-09-17.

| Dimension | moka 0.12.16 | cached 4.0.0 | lru 0.18.4 |
|:---|:---|:---|:---|
| GitHub stars | 2,683 | 2,085 | 835 |
| Last commit | 2026-08-09 | 2026-09-05 | 2026-09-03 |
| License | Apache-2.0 | MIT | MIT |
| Primary use | Concurrent cache engine | Function memoization | Standalone LRU structure |
| `get` receiver | `&self` (lock-free reads) | macro-generated | `&mut self` (exclusive) |
| Eviction policy | TinyLFU admission + LRU eviction | User-selected cache type | Strict LRU |
| Bound by entry count | ✅ | ✅ | ✅ |
| Bound by weighted size | ✅ | ❌ | ❌ |
| Per-entry TTL | ✅ | ✅ via macro args | ❌ |
| Async-aware cache | ✅ (`moka::future`) | ✅ (`#[concurrent_cached]`) | ❌ |
| Eviction listener | ✅ | Partial | ❌ (returned value only) |
| Sharded variant | ❌ (not needed) | ✅ `ShardedLruCache` | ❌ |
| Background threads | Removed in v0.12 | None | None |
| Dependency weight | Heavier | Moderate | Minimal |

## Decision Matrix: Pick In Ten Seconds

| Your situation | Choose | Why |
|:---|:---|:---|
| Shared cache behind a REST/gRPC handler | **moka** | `&self` reads + TinyLFU hit ratio under Zipfian traffic |
| Caching a pure function (derives, parsing, hashing) | **cached** | `#[cached]` on the function, done in one line |
| Caching an async database call | **moka future** or **`#[concurrent_cached]`** | Per-key atomic loaders prevent stampedes |
| Values are large and entry count is a bad bound | **moka** | Weigher bounds by bytes, not by keys |
| Single-threaded parser or CLI inner loop | **lru** | No locks, no atomics, negligible overhead |
| You want to control sharding yourself | **lru** | Wrap `N` LRUs behind your own striped locks |
| Zero-dependency policy in a library crate | **lru** | Smallest transitive tree of the three |

## moka: The Concurrent Engine

Moka is explicitly inspired by Caffeine, the Java cache library that most JVM engineers already trust. Two design decisions matter more than anything else in this comparison:

1. **Reads do not take an exclusive lock.** `Cache::get(&self, &K)` lets concurrent readers proceed without serializing on a single mutex. On an 8-core box serving read-heavy traffic, this is the difference between a cache that scales and a cache that becomes your bottleneck.
2. **Admission is separated from eviction.** Moka uses a **TinyLFU** admission filter with an **LRU** eviction policy: a new key has to prove it is more valuable than what is already resident before it is allowed to displace anything. This is why moka holds up on access patterns where 20% of keys get 80% of requests.

```toml
# Cargo.toml — the sync cache lives behind the `sync` feature
[dependencies]
moka = { version = "0.12", features = ["sync"] }
```

```rust
use moka::sync::Cache;

fn main() {
    // Capacity-bounded and thread-safe. Cloning a cache is cheap
    // (it is an Arc internally), so share it freely across threads.
    let cache: Cache<String, String> = Cache::new(10_000);

    cache.insert("user:42".to_string(), "ada".to_string());
    assert_eq!(cache.get(&"user:42".to_string()), Some("ada".to_string()));

    // get_with is atomic per key: if 100 threads miss at once, the loader
    // runs once and the other 99 wait for that same value. No stampede.
    let name = cache.get_with("user:99".to_string(), || expensive_lookup("user:99"));
    println!("{name}");
}
```

Moka's own README ships a frank trade-off table admitting that moka "can be overkill," pointing at **mini-moka** (0.10.3) for single-threaded use and **quick_cache** (0.7.0) when you want a sharded cache with a very small overhead over a concurrent hash map. That honesty is worth respecting: if your workload is one thread doing 200 lookups a second, moka's machinery is not buying you anything.

The feature that is hard to find elsewhere is **weighted bounding**. Instead of `Cache::new(10_000)` you declare a weigher, and the cache evicts by total bytes:

```rust
use moka::sync::Cache;

let cache: Cache<String, Vec<u8>> = Cache::builder()
    .max_capacity(64 * 1024 * 1024)          // budget in bytes
    .weigher(|_key, value: &Vec<u8>| value.len() as u32)
    .time_to_live(std::time::Duration::from_secs(300))
    .build();
```

For pages, thumbnails, serialized JSON blobs and anything where one key can be 100 KB and another 200 bytes, entry-count bounding is simply the wrong instrument. Moka also supports `time_to_idle`, per-entry variable expiry and an eviction listener for metrics.

## cached: Memoization As A Language Feature

If moka is infrastructure, `cached` is ergonomics. Version 4.0 consolidated years of macro evolution into a single attribute you put on a function:

```toml
[dependencies]
cached = { version = "4.0", features = ["proc_macro"] }
```

```rust
use cached::proc_macro::cached;

// The entire cache is declared by one attribute. Default bound: 32 entries.
#[cached]
fn fib(n: u64) -> u64 {
    if n < 2 { n } else { fib(n - 1) + fib(n - 2) }
}

// Size, TTL and key conversion are all attribute arguments.
#[cached(size = 500, time = 600, key = "String")]
fn render_report(user_id: u64, template: String) -> String {
    format!("report for {user_id} using {template}")
}
```

The macro family has grown into three variants worth knowing:

- `#[cached]` — synchronous, works with any `cached::Cached` implementation.
- `#[concurrent_cached]` — for values shared across threads, with a sharded default.
- `#[once]` — compute exactly once for the process lifetime; ideal for config and connection handles.

You are not limited to the macro. The crate also exposes concrete types, and 4.0 added sharded concurrent caches that attack exactly the lock-contention problem the plain `lru` crate pushes onto you:

```rust
use cached::ShardedLruCache;

// 10 shards: contention on one big lock becomes contention on ten small ones.
let sharded: ShardedLruCache<String, u32> = ShardedLruCache::new(10);
sharded.set("alpha".to_string(), 1);
assert_eq!(sharded.get("alpha"), Some(1));
```

Note the signature difference from moka: `ShardedLruCache::get` takes a shared reference and returns an owned `Option<V>`, not `Option<&V>`. That is deliberate — you cannot hold a reference into a shard while another thread mutates it. If you build caches that return borrowed values, that single design decision will reshuffle your code.

## lru: The Honest Data Structure

The `lru` crate makes no promises about concurrency, and that is its strength. It is a strict least-recently-used map with a minimal dependency tree — the kind of crate you can drop into a library without imposing a supply-chain decision on your users.

```rust
use lru::LruCache;
use std::num::NonZeroUsize;

fn main() {
    let mut cache = LruCache::new(NonZeroUsize::new(100).unwrap());

    cache.put("alpha", 1);
    assert_eq!(cache.get(&"alpha"), Some(&1));

    // peek inspects without promoting the entry to most-recently-used.
    assert_eq!(cache.peek(&"alpha"), Some(&1));

    // push returns the evicted pair when the cache is full.
    if let Some((key, value)) = cache.push("beta", 2) {
        println!("evicted {key} -> {value}");
    }

    assert_eq!(cache.cap().get(), 100); // capacity is queryable
}
```

The critical detail for backend engineers is in the method signatures: **`get`, `peek` and `pop` all take `&mut self`.** An LRU list is a mutable structure by construction — reading an entry reorders the list, so a read is a write. The consequence is unavoidable:

```rust
use lru::LruCache;
use std::num::NonZeroUsize;
use std::sync::Mutex;

// This compiles and works — but every read now serializes every other reader.
let shared: Mutex<LruCache<String, Vec<u8>>> =
    Mutex::new(LruCache::new(NonZeroUsize::new(1_000).unwrap()));

fn read(shared: &Mutex<LruCache<String, Vec<u8>>>, key: &str) -> Option<Vec<u8>> {
    let mut guard = shared.lock().unwrap();
    guard.get(key).cloned()          // clone out: we cannot return a borrow
}
```

An `RwLock` does **not** fix this. Because `get` needs exclusive access, the read path must take the write lock, so `RwLock<LruCache<..>>` gives you the same serialization with extra bookkeeping. The fix is sharding: keep `N` independent LRUs and route keys by hash, which is precisely what `cached::ShardedLruCache` does for you. Use `lru` directly when the structure is thread-local — a request-scoped buffer, a parser's memo table, a single-threaded worker — and reach for a sharded or concurrent cache the moment two threads share it.

## Pitfalls That Bite In Production

**Unbounded growth is the default mistake.** `moka::sync::Cache::new(n)` and `LruCache::new(cap)` are both bounded, but the moment you reach for `HashMap` "just for now," you have opted out of eviction. Decide the bound before you write the first `insert`.

**You must clone on the read path with exclusive caches.** Exclusive caches cannot hand out references. If your values are large structs, that clone is a real cost — budget for it, or store `Arc<T>` and clone the pointer.

**Entry count is a poor proxy for memory.** 10,000 keys of 200 bytes is 2 MB; 10,000 keys of 500 KB is 5 GB. If value size varies, use moka's weigher.

**Cache stampedes are real under load.** A cold cache plus 1,000 concurrent requests equals 1,000 identical database queries. Moka's `get_with` and `try_get_with` collapse those into one; with `lru` you have to build that coordination yourself.

**TTL is not invalidation.** A 300-second TTL means up to 300 seconds of stale reads. For user-owned data, invalidate on write *and* keep a short TTL as a backstop.

**Instrument the hit ratio from day one.** A cache with a 12% hit ratio is pure overhead — extra memory, extra code paths, no benefit. Export hits, misses and evictions and watch them for a week before you trust the design.

## Choosing Inside A Real Stack

In an axum or actix service, the usual shape is one `moka::future::Cache` per logical dataset, built once in shared state and passed to handlers. If you are still evaluating your web layer, our [Rust web framework comparison](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/) covers how state is shared across actix, Rocket and axum, and the [second-generation Rust framework round-up](../2026-09-07-rust-web-frameworks-loco-salvo-poem-comparison/) covers Loco, Salvo and Poem. Caching also shows up in less obvious places: parsers memoize intermediate rules, which is why the [Rust parsing library comparison](../2026-07-30-rust-parsing-libraries-nom-pest-lalrpop-chumsky-combine-winnow/) is worth reading before you hand-roll a memo table. And if your cache is really a hot in-process dataset, the same trade-offs appear in the [.NET in-memory caching comparison](../2026-08-02-csharp-inmemory-caching-libraries-memorycache-lazycache-fusioncache/) — the policy vocabulary is identical even though the runtimes are not.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Moka vs cached vs lru in 2026: Which Rust Cache Crate Should You Actually Use?",
  "description": "A hands-on comparison of moka 0.12, cached 4.0 and lru 0.18 for Rust caching in 2026, covering concurrency semantics, eviction policies, real code examples and production pitfalls.",
  "datePublished": "2026-09-17",
  "dateModified": "2026-09-17",
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

## FAQ

**Is moka faster than the `lru` crate?**

Not in raw single-threaded operation — `lru` has almost no overhead beyond a `HashMap`, and it wins narrowly when only one thread touches the cache. Moka pulls ahead the moment concurrency enters the picture: its reads take a shared reference instead of an exclusive one, so 16 threads can miss and hit in parallel instead of queueing behind a mutex. If your cache is thread-local, use `lru`; if it is shared, moka's parallelism beats `lru` wrapped in a lock by a wide margin.

**Can I cache async functions with `cached`?**

Yes. Use `#[concurrent_cached]` for values shared across tasks, which ships with a sharded default, or `#[cached]` where the cached function is not itself awaiting. If you would rather control the loader manually, `moka::future::Cache::get_with` accepts a future and guarantees the loader runs once per key even when many tasks request the same missing key simultaneously.

**Does the `lru` crate support TTL or expiry?**

No. `lru` is a bounded map with a recency policy and nothing else — there is no time-based expiry, no eviction listener and no metrics. If you need TTL, either layer timestamps into your value type and check them on read, or switch to `moka` (which supports `time_to_live`, `time_to_idle` and per-entry variable expiry) or `cached` (whose macros accept `time`, `ttl` and `ttl_millis` arguments).

**How do I bound a cache by memory instead of entry count?**

Use moka's `weigher` together with `max_capacity`: the weigher returns a per-entry cost, typically `value.len()`, and the cache evicts until total weight fits the budget. This is the correct approach whenever value sizes vary by more than an order of magnitude — thumbnails, rendered pages, serialized payloads. Neither `cached` nor `lru` supports weighted bounds, so a byte-budget cache is one of the few features that genuinely forces the moka decision.

**Do I need to wrap a cache in `Arc`?**

With moka, no — cloning a `Cache` is cheap because it already holds its storage behind shared ownership, so clone it into handlers and tasks freely. With `cached`'s concrete types you usually own the cache in application state and access it through a reference. With `lru` you must supply your own `Arc` or `Mutex`, because the type is a plain structure with no internal sharing.

**Which cache should I use with axum or tokio?**

`moka::future::Cache` is the natural fit: its async API is futures-aware, `get_with` prevents duplicate in-flight loads, and its reads do not block the runtime. Reach for `#[concurrent_cached]` when the cached unit is a pure async function rather than a dataset, and reserve `lru` for per-request or per-task scratch structures where no sharing occurs.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
