---
title: "lru-cache vs node-cache vs quick-lru: Node.js In-Memory Caching in 2026"
date: "2026-09-01"
tags: ["comparison", "guide", "nodejs", "caching", "performance", "developer-tools"]
draft: false
description: "Compare lru-cache, node-cache, and quick-lru — the three dominant in-memory caching libraries for Node.js — across eviction policies, TTL semantics, memory accounting, and maintenance, with real code and benchmarks guidance for 2026."
---

Your database is the slowest thing in your stack, and you are probably hitting it more than you think. A hot endpoint that runs one query per request can be made 10-100x faster with a single line of caching — which is why in-memory caching libraries are among the most-downloaded packages in the Node ecosystem. But the three dominant options solve subtly different problems: **lru-cache** (5,912 stars) is the industrial-grade standard with configurable eviction and size accounting, **node-cache** (2,372 stars) is the simple TTL key-value store that has powered a generation of prototypes, and **quick-lru** (767 stars) is a tiny, focused LRU from the sindresorhus toolkit. Pick the wrong one and you get either an over-engineered dependency or a cache that silently grows without bound. Here is how to choose.

## TL;DR — Quick Verdict

- **Choose lru-cache** for production services: it is the only one of the three with real memory accounting (`maxSize` + `sizeCalculation`), per-item TTL, and battle-tested eviction semantics — the default choice of npm itself.
- **Choose node-cache** when you need a dead-simple TTL store with event hooks (`expired`, `flush`) and no eviction complexity — ideal for session data and quick wins.
- **Choose quick-lru** when you want a minimal, dependency-free LRU with Map semantics and clean iteration — perfect for libraries and tools that should not drag in a heavyweight dependency.

## Feature Comparison at a Glance

| Feature | lru-cache | node-cache | quick-lru |
|---|---|---|---|
| GitHub stars (2026-09) | 5,912 | 2,372 | 767 |
| Last push (2026) | Jul 07 | Jun 2024 | Jul 09 |
| Eviction policy | LRU + configurable | None (TTL only) | LRU |
| Max item count | Yes (`max`) | No | Yes (`maxSize`) |
| Memory size accounting | Yes (`maxSize` + `sizeCalculation`) | No | No |
| Per-item TTL | Yes (`ttl` option) | Yes (`stdTTL`) | No |
| Refresh on access | Yes (`updateAgeOnGet`) | No | No (age on set) |
| Events / hooks | `set`/`get`/`dispose` options | `expired`, `flush`, `del` events | None |
| Async disposal | Yes (`fetchMethod`, dispose async) | No | No |
| ESM + CJS | Both (v10+) | CJS (+ ESM wrapper) | Both |
| Iteration | Map-compatible | Keys/values lists | Map-compatible |
| Dependencies | Zero | Zero | Zero |

## Decision Matrix — Use Case → Tool → Why

| Use Case | Recommended Library | Reasoning |
|---|---|---|
| Caching database results in a service | lru-cache | Size accounting prevents memory blowups; TTL + refresh keep data fresh |
| HTTP response caching with varying payload sizes | lru-cache | `maxSize`/`sizeCalculation` bounds memory, not just item count |
| Session tokens / short-lived ephemeral data | node-cache | TTL-first design and expiry events match session lifecycles |
| A library author adding a small cache | quick-lru | 300 lines, zero deps, Map-compatible — no bloat for consumers |
| Fixed-size memoization of function calls | lru-cache or quick-lru | Both handle bounded LRU; lru-cache if you also need TTL |
| Legacy codebase on CJS | node-cache or lru-cache | Both work in CommonJS without build steps |

## lru-cache — The Production Standard

**Repository**: [isaacs/node-lru-cache](https://github.com/isaacs/node-lru-cache) — 5,912 stars, last updated July 7, 2026.

lru-cache is the oldest and most feature-complete of the three, and it is the cache npm uses internally. Its defining capability is **real memory accounting**: instead of capping by item count alone, you can cap by total estimated bytes, with a per-item `sizeCalculation` function. Combined with `ttl`, `updateAgeOnGet`, and async `fetchMethod` (which deduplicates concurrent cache misses), it covers production caching scenarios that the simpler libraries simply cannot.

```js
import { LRUCache } from 'lru-cache';

const cache = new LRUCache({
  max: 500,                         // fallback: max item count
  maxSize: 50 * 1024 * 1024,        // hard cap: 50 MB total
  sizeCalculation: (value) => JSON.stringify(value).length,
  ttl: 1000 * 60 * 5,               // 5-minute TTL
  updateAgeOnGet: true,             // touch LRU position on read
  dispose: (value, key) => {
    // called when an item is evicted or expires — close handles, etc.
  },
});

cache.set('user:42', profile);
const profile = cache.get('user:42');   // null after TTL
cache.set('token:7', token, { ttl: 60_000 }); // per-item TTL override
cache.delete('user:42');
```

The v10+ rewrite made it fully dual ESM/CJS, added `ttlResolution` tuning, and made `fetchMethod` the recommended way to load values with automatic deduplication:

```js
const cache = new LRUCache({
  max: 100,
  ttl: 60_000,
  fetchMethod: async (key) => {
    // only ONE in-flight fetch per key, even under a thundering herd
    return db.query('SELECT * FROM items WHERE id = ?', [key]);
  },
});
const item = await cache.fetch('item:5');
```

**Where it shines:** production-grade eviction and size control, zero dependencies, and an API that has survived a decade of real-world use. **Where it hurts:** the options surface is large — for a 50-line utility script, it is more library than you need.

## node-cache — The Simple TTL Store

**Repository**: [node-cache/node-cache](https://github.com/node-cache/node-cache) — 2,372 stars, last pushed June 2024.

node-cache is a TTL-first key-value store: values expire after `stdTTL` seconds, a background `checkperiod` sweeps expired keys, and events let you react to expirations. It has no eviction policy — if you keep inserting without expiring, memory grows — but for session data and short-lived state, that is exactly the behavior you want. Note the maintenance cadence: the repo's last push was June 2024, so it is stable rather than actively evolving.

```js
const NodeCache = require('node-cache');
const cache = new NodeCache({ stdTTL: 300, checkperiod: 60 });

cache.set('user:42', userProfile);       // expires in 300s
const profile = cache.get('user:42');    // undefined if expired
cache.getTtl('user:42');                 // remaining TTL in ms
cache.del('user:42');
cache.flushAll();

// React to expiry — handy for cleaning up related state
cache.on('expired', (key, value) => {
  console.log(`session ${key} expired`);
});
```

A frequent pattern is combining `stdTTL: 0` (no default expiry) with per-key TTLs via the options argument of `set`, which gives you TTL control without a global policy.

**Where it shines:** the simplest possible mental model — keys expire, events fire, everything else is your job. **Where it hurts:** no LRU eviction means an unlucky workload grows memory until you intervene, and the slower release cadence means newer Node features arrive late.

## quick-lru — The Minimalist LRU

**Repository**: [sindresorhus/quick-lru](https://github.com/sindresorhus/quick-lru) — 767 stars, last updated July 9, 2026.

quick-lru is a deliberately tiny LRU from the sindresorhus toolkit (the maintainer behind dozens of essential npm packages). It implements a clean LRU with a hard `maxSize`, Map-compatible iteration, and nothing else — no TTL, no events, no size calculation. For library authors, that minimalism is the feature: adding it costs almost nothing for consumers.

```js
import QuickLRU from 'quick-lru';

const cache = new QuickLRU({ maxSize: 1000 });

cache.set('key', 'value');
cache.get('key');          // 'value' — or undefined if evicted
cache.has('key');
cache.delete('key');
cache.clear();

// Map-compatible iteration in insertion order
for (const [key, value] of cache) {
  console.log(key, value);
}
// Methods return the cache, so chains work:
cache.set('a', 1).set('b', 2).get('a');
```

Under the hood it uses a doubly-linked list plus a Map for O(1) operations, and when the cache is near-full it evicts the least-recently-used entry — with a small optimization that skips eviction churn when you delete keys you just set.

**Where it shines:** zero dependencies, zero config, and iteration semantics that make it a drop-in Map replacement. **Where it hurts:** no TTL support at all — if you need time-based expiry, you must build it on top, which makes it the wrong base for most server-side caching.

## Pitfalls and Caching Mistakes

1. **Unbounded caches are the classic production incident.** Every library here except quick-lru/lru-cache with `max` lets you insert indefinitely. Always set `max` or `maxSize` in production — a cache that grows with your request volume is a memory leak wearing a costume.
2. **TTL is not the same as freshness.** A 5-minute TTL on a cache whose data changes every 10 seconds will serve stale responses. Match TTLs to your real invalidation budget, or use `fetchMethod` with revalidation.
3. **In-memory caching is per-process.** These libraries cache within one Node process. Behind a load balancer with four instances, each has its own copy — for cross-instance consistency you need a shared store (Redis, or a distributed cache layer) alongside or instead of the in-memory tier.
4. **Never cache user-specific data under a global key.** Cache keys must include the identity that scopes the data (`user:42`, not `profile`), or one user sees another user's data. This is the most common correctness bug in hand-rolled caching.
5. **`JSON.stringify` in `sizeCalculation` costs time.** On hot paths, estimate size arithmetically (e.g., `(value?.length ?? 0) * 2` for strings) instead of serializing on every write.
6. **Beware cache stampedes.** When a key expires, dozens of concurrent requests can all miss and hammer the database. Use lru-cache's `fetchMethod` (deduplicates in-flight fetches) or implement a mutex key pattern yourself.
7. **Node's built-in `Map` is not a cache.** It has no eviction, no TTL, and no size bound. Using `Map` directly for caching is how many projects accidentally grow unbounded — the libraries above exist for a reason.

## Why Caching Is the Highest-ROI Performance Work

A single cache line on a hot endpoint routinely turns a 120 ms database round-trip into a 1 ms memory read — a 100x improvement that no index tuning, query optimization, or hardware upgrade matches for the same effort. And unlike distributed caches, an in-process cache adds no network hop, no serialization, and no operational moving parts: it is the fastest possible read path your application can have.

The trade-off is that in-memory caches are local and ephemeral. The pattern that wins in practice is a two-tier design: a small, fast in-process LRU in front, with a shared store behind it for consistency across instances. For the Node.js tier, the libraries above are the pick of the field; if you need durable, cross-process caching, pair them with a proper store such as Redis. The same reasoning applies across languages — our [Python caching library comparison](../2026-06-22-python-caching-libraries-cachetools-diskcache-dogpile-guide/) and [Go cache library guide](../2026-06-19-self-hosted-cache-libraries-golang-lru-gocache-bigcache-tinylfu/) cover the equivalent options for those ecosystems. And when the cache misses, the database drivers you chose determine how painful the miss is — see our [Node.js database driver comparison](../2026-08-24-nodejs-database-drivers-better-sqlite3-pg-mysql2-comparison/) for what sits beneath the cache layer.

## FAQ

**What is the difference between LRU eviction and TTL expiry?**
LRU eviction removes the least-recently-used items when the cache reaches its size cap — it manages *memory*. TTL expiry removes items whose age exceeds a timeout — it manages *freshness*. lru-cache supports both independently; node-cache only does TTL; quick-lru only does LRU.

**Which library does npm itself use?**
lru-cache. The npm CLI and registry tooling rely on it for metadata caching, which is a strong real-world endorsement of its stability and performance under heavy load.

**Can I use these libraries in browser or edge runtimes?**
Yes. All three are plain JavaScript with zero Node-specific dependencies (lru-cache v10+ and quick-lru are ESM-first and run in browsers and edge workers). node-cache uses `setInterval` for its checkperiod, which behaves differently in some edge environments — test before relying on expiry sweeps there.

**How do I benchmark cache hits vs database queries?**
Compare end-to-end latency with `console.time`/`performance.now()` around both paths, or use a load-testing tool against an endpoint with and without caching. The difference is usually visible at very low request rates (single-digit QPS) because a single cache hit is microseconds versus milliseconds for a query.

**Is it safe to cache objects by reference?**
Only if you never mutate them after insertion. lru-cache and node-cache store references, so a caller that mutates a cached object corrupts the cache. Defensive copies (structuredClone or serialization) cost performance; the usual compromise is documenting the contract and freezing objects you cache.

**How do these compare to Redis?**
In-memory libraries are single-process, zero-configuration, and faster (no network hop), but they do not survive restarts and do not synchronize across instances. Redis adds durability, cross-instance sharing, and pub/sub invalidation at the cost of an external dependency and network latency. Most production systems use both: in-memory L1 in front of Redis as L2.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "lru-cache vs node-cache vs quick-lru: Node.js In-Memory Caching in 2026",
  "description": "Compare lru-cache, node-cache, and quick-lru — the three dominant in-memory caching libraries for Node.js — across eviction policies, TTL semantics, memory accounting, and maintenance, with real code and benchmark guidance for 2026.",
  "datePublished": "2026-09-01",
  "dateModified": "2026-09-01",
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
