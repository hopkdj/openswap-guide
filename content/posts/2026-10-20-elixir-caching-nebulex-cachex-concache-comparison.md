---
title: "Elixir Caching in 2026: Nebulex vs Cachex vs ConCache — Which One Should You Ship?"
date: "2026-10-20"
tags: ["elixir", "caching", "performance", "backend"]
draft: false
cover: "/img/screenshots/nebulex-logo.jpg"
description: "A hands-on comparison of Nebulex, Cachex and ConCache for Elixir: real code, adapter models, distributed topologies, telemetry and the operational traps nobody documents."
---

Your Phoenix app is fast until it isn't. The first request that hits a slow query, a flaky upstream API or an expensive JSON encode is fine — the ten-thousandth one, all at once, is what takes your node down. Every Elixir team eventually reaches for a cache, and then discovers the awkward truth: the BEAM gives you ETS for free, but ETS alone gives you no expiry policy, no stampede protection, no telemetry, and no story for what happens when you run four nodes behind a load balancer.

That gap is why three libraries dominate the conversation: **Cachex**, **ConCache** and **Nebulex**. They look interchangeable in a README, but they encode three very different philosophies — a batteries-included cache server, a minimal ETS wrapper, and an Ecto-style abstraction layer with pluggable adapters.

## TL;DR — the 30-second verdict

**Ship Cachex** if you want a production cache with TTL, fallbacks, transactions and async writes, and you are happy with a single-node (or manually coordinated) design. **Ship ConCache** if you want the thinnest possible layer over ETS with row-level isolated writes and you intend to own the concurrency design yourself. **Ship Nebulex** if you need one API across local, Redis and Memcached backends, or if you want declarative `@decorate cacheable` functions instead of manual key management. In 2026 that last point is the deciding factor for most teams: Nebulex is the only one of the three that treats "which backend" as a configuration detail rather than an architectural commitment.

## Side-by-side comparison

| Dimension | Cachex | ConCache | Nebulex |
|---|---|---|---|
| GitHub stars | **1,745** | 927 | 1,404 |
| Last commit | 2026-02-10 | 2025-09-29 | **2026-10-18** |
| Core model | GenServer + ETS, one process per cache | Thin ETS wrapper, owner process only for TTL checks | Behaviour + adapter (Local, Redis, Memcached, replicated) |
| Distributed caching | No (single node) | No (single node) | **Yes — adapter-level** |
| Declarative decorators | No | No | **Yes (`@decorate cacheable`)** |
| TTL support | Yes, per-key | Yes, global + per-key override | Yes, adapter-dependent |
| Transactions / atomic ops | **Yes (`Cachex.transaction/3`)** | Isolated writes per row | Yes (`get_or_store`, transactions in local adapter) |
| Fallbacks on miss | **Yes (`fallback:` option)** | No | Yes (`fetch_or_store`, `get_or_store`) |
| Telemetry | Stats via `Cachex.stats/1` | `:telemetry` events | Built-in `:telemetry` + Info API |
| Supervision | `{Cachex, [:name]}` child spec | Your tree owns the owner process | `use Nebulex.Cache` module in your tree |
| Learning curve | Low | **Lowest** | Medium (adapter + decorator concepts) |

Star counts and last-commit dates were pulled from the public repositories on 2026-10-20.

## Use-case decision matrix

| If your situation is… | Pick | Why |
|---|---|---|
| Single node, need TTL + fallbacks today | **Cachex** | Zero ceremony, everything in one module |
| You want raw ETS speed and will handle races yourself | **ConCache** | Row-level isolated writes, no GenServer bottleneck on reads |
| Multi-node cluster with Redis already deployed | **Nebulex** | Swap `Nebulex.Adapters.Redis` in, keep the same call sites |
| You hate manual key building | **Nebulex** | `@decorate cacheable` derives keys from function args |
| Batch cache warming (thousands of keys) | **Cachex** | `put_many/3` amortises the round trip |
| You need cache + distributed locks + counters | **Nebulex** | Wider primitive set, adapter-agnostic |

## Cachex — the pragmatic default

Cachex is the library most Elixir teams reach for first, and the reason is that it answers the questions you actually have on day one. Starting it inside your supervision tree takes one line:

```elixir
children = [
  {Cachex, [:my_cache]},     # with default options
  {Cachex, [:my_cache, []]}  # with custom options
]
```

The API is deliberately boring, which is a compliment:

```elixir
{:ok, _pid} = Cachex.start_link(:my_cache)

:ok = Cachex.put(:my_cache, "my_key", "my_value")
true = Cachex.exists?(:my_cache, "my_key")
"my_value" = Cachex.get(:my_cache, "my_key")
:ok = Cachex.del(:my_cache, "my_key")
```

Where Cachex pulls ahead of a naive ETS wrapper is the option surface on reads. A single call can install a TTL, define a fallback, and mark the write as asynchronous:

```elixir
# Cache for 10 minutes, compute on miss, don't block the caller
Cachex.get(:my_cache, "user:#{id}",
  fallback: fn _key ->
    Users.fetch!(id)
  end
)
```

Three behaviours here matter operationally. `fallback` collapses the "check, miss, compute, store" dance into one call, which removes the most common source of duplicated work in Elixir codebases. `Cachex.transaction/3` gives you atomic read-modify-write for counters and rate limiters without hand-rolling `:ets.update_counter` semantics. And `put_many/3` exists specifically so that warming a thousand keys is one GenServer message instead of a thousand:

```elixir
:ok = Cachex.put_many(:my_cache, [
  {"key1", 1},
  {"key2", 2},
  {"key3", 3}
])
```

The trade-off is architectural: Cachex is per-node. If you run three nodes and each one caches independently, your hit ratio is fine but your invalidation story is not. Teams routinely "solve" this by lowering TTLs until the cache stops helping. If you recognise that pattern in your own metrics, you don't have a Cachex problem — you have an architecture problem, and Nebulex is the honest answer.

## Nebulex — the Ecto of caching

Nebulex's README makes the analogy explicit: like Ecto, it is an abstraction you write against, with backends behind it. You declare a cache module once:

```elixir
defmodule MyApp.Cache do
  use Nebulex.Cache,
    otp_app: :my_app,
    adapter: Nebulex.Adapters.Local
end
```

…add it to your supervision tree like any other child, and then use it as a namespace:

```elixir
iex> MyApp.Cache.put("foo", "bar")
:ok
iex> MyApp.Cache.fetch("foo")
{:ok, "bar"}
```

Dependencies are opt-in, which keeps the footprint honest — you only pull what you use:

```elixir
def deps do
  [
    {:nebulex, "~> 3.0"},
    {:nebulex_local, "~> 3.0"}, # Generational local cache adapter
    {:decorator, "~> 1.4"},     # Required for caching decorators
    {:telemetry, "~> 1.0"}      # Required for telemetry events
  ]
end
```

The feature that changes how you write code is declarative caching. Instead of threading keys through your application, you annotate the function:

```elixir
defmodule MyApp.Users do
  use Nebulex.Caching
  alias MyApp.Cache

  @decorate cacheable(cache: Cache, key: {:user, id}, opts: [ttl: :timer.minutes(10)])
  def get_user(id) do
    Repo.get!(User, id)
  end

  @decorate cache_evict(cache: Cache, keys: [{:user, id}])
  def update_user(id, attrs) do
    Repo.update!(...)
  end
end
```

Two consequences follow. First, key construction becomes a compiler-visible convention rather than string interpolation scattered across modules — the single biggest cause of "cache never invalidates" bugs. Second, swapping the local generational cache for `Nebulex.Adapters.Redis` in a multi-node deployment is a one-line adapter change plus a dependency, not a rewrite of every call site. The generational local adapter also gives you a coarse but effective answer to memory pressure: bump the generation and old entries fall out of the read path.

Nebulex is the most recently active of the three (last commit 2026-10-18), which matters if you are standing up a new service in 2026 rather than maintaining a 2021 codebase.

## ConCache — the minimal ETS layer

ConCache optimises for a different thing entirely: predictable, isolated writes over an ETS table, with as little machinery as possible between your code and the memory. You start it, name it, and put it in your tree:

```elixir
children = [
  {ConCache, [name: :my_cache, ttl_check_interval: false]},
  # ...
]
```

That `ttl_check_interval: false` is not a detail — it disables the periodic sweep. ConCache will still honour per-item TTL on read, but if you want background expiry you set an interval; if you want zero overhead you turn it off and accept that stale entries occupy memory until they are read or evicted. Very few libraries let you make that trade-off explicitly, and for high-throughput read-heavy caches it is the right call.

ConCache's design docs are unusually candid about process ownership: `start_link` creates a *cache owner* process that owns the ETS table and performs TTL checks, and **no other operation runs in that process**. Gets and puts touch ETS directly from the calling process. That is why ConCache reads scale with scheduler count rather than serialising through a single GenServer, and it is also why write isolation matters — the library documents row-level isolated writes precisely because concurrent read-modify-write on the same key is your problem to solve, not the library's.

Telemetry is available for hit and miss accounting:

```elixir
defmodule MyApp.HitMissRatioTracker do
  require Logger

  def handle_event([:con_cache, :stats, :hit], _measurements, %{cache: %{name: cache_name}}, _config) do
    # ... aggregate hits
  end
end
```

The honest summary: ConCache is excellent when your access pattern is "read a lot, write rarely, know exactly which keys collide". It is a poor fit when you want fallbacks, transactions, or cross-node coherence, because it deliberately doesn't have them. Its last commit (2025-09-29) is the oldest of the three, which is not abandonment — the surface is stable and small — but you should weigh it if you need active feature development.

## Performance and memory: what actually breaks first

All three sit on ETS, so raw single-key throughput is not where the decision lives. What differs:

- **Serialisation.** Cachex routes operations through a cache process; ConCache reads bypass it; Nebulex's local adapter is ETS-backed with its own coordination. At extremely high op rates, the bypass matters.
- **Memory growth.** Without a sweep, expired-but-unread entries stay resident. ConCache with `ttl_check_interval: false` and Cachex without a max-size policy will both grow until the node's memory alarms fire. Set a size limit and a default TTL, always.
- **Copy semantics.** Every value you store is copied into the ETS table and copied back out on read. A 2 MB decoded API response cached "for speed" will cost you 2 MB per read in copying alone. Cache identifiers and small structs, not page payloads.
- **Distributed hops.** Redis-backed Nebulex turns a sub-microsecond local read into a network round trip. That can still be a 100× win over your database, but it is not free and it is not local.

## Pitfalls that bite in production

**1. Storing PIDs and references.** ETS copies terms, but a cached PID belongs to the node that created it. Cache data, never process handles.

**2. Unbounded key cardinality.** `"session:#{uuid}"` for every request is not a cache, it is a memory leak with extra steps. Always pair high-cardinality keys with a TTL.

**3. Stampede on cold start.** Cachex's `fallback` and Nebulex's `get_or_store` reduce duplication but do not guarantee single-flight under a thundering herd. For expensive computations, wrap the loader in a `:global.trans` or a per-key lock.

**4. Invalidation across nodes.** If node A evicts and node B still holds the value, you have introduced a correctness bug that only appears under load. Either use a shared backend (Nebulex + Redis) or make TTLs short enough that staleness is bounded by design.

**5. Treating cached data as authoritative.** The cache is a copy. Any code path that reads the cache and skips the database on a write path will eventually resurrect deleted records.

**6. Forgetting telemetry until an incident.** Wire hit/miss counters on day one. A cache with a 20% hit rate is usually a key-design bug, and you cannot see it without instrumentation.

If you are also running external caches in the same stack, our [in-memory caching engines comparison](../2026-06-20-self-hosted-in-memory-caching-caffeine-cache2k-ohc-guava/) covers the JVM side of the same trade-offs, and the [Redis high availability guide](../2026-05-15-self-hosted-redis-high-availability-sentinel-cluster-keydb-guide/) is the reference for keeping a shared backend alive when Nebulex points at it. For teams comparing embedded stores at the edge, the [embedded database comparison](../2026-09-17-dotnet-embedded-databases-litedb-fasterkv-sqlite-comparison/) is a useful sanity check on what "local, fast, durable" really costs.

## FAQ

**Which Elixir caching library is fastest?**
For single-key reads on one node, ConCache is typically the leanest because reads go straight to ETS without passing through a cache process. Cachex adds a process hop but gives you TTL, fallbacks and transactions. Nebulex's local adapter is competitive; its Redis adapter trades microseconds for cross-node coherence.

**Can Cachex work across multiple nodes?**
Not natively. Cachex is a per-node cache. You can run one per node and accept independent invalidation, or move to a shared backend. Nebulex is the library in this comparison designed for that transition because the adapter is swappable without changing call sites.

**Do I need Nebulex if I only use one node?**
No — but the decorator API is still worth it if you dislike manual key building. `@decorate cacheable` derives keys from function arguments and pairs the read with a matching `cache_evict`, which removes a whole class of stale-cache bugs.

**How do I stop an ETS-backed cache from eating all memory?**
Set a default TTL and a maximum size, and never cache unbounded key cardinality. With ConCache, keep `ttl_check_interval` enabled unless you have measured the sweep as a bottleneck; with Cachex, use the limit options rather than relying on expiry alone.

**Is ConCache abandoned?**
Its last commit was 2025-09-29, which is slower than the other two but consistent with a small, stable surface. Evaluate it for what it is — a thin ETS layer — not for features it never promised.

**What about using plain ETS directly?**
Reasonable for fixed-size lookup tables built at boot. The moment you need expiry, eviction policy, statistics or a fallback loader, you are reimplementing a cache library badly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Elixir Caching in 2026: Nebulex vs Cachex vs ConCache — Which One Should You Ship?",
  "description": "Hands-on comparison of Nebulex, Cachex and ConCache for Elixir: adapter models, distributed topologies, telemetry, real code and production pitfalls.",
  "datePublished": "2026-10-20",
  "dateModified": "2026-10-20",
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
