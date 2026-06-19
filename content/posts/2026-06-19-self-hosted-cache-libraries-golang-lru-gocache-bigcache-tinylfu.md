---
title: "Self-Hosted In-Memory Cache Libraries: golang-lru vs go-cache vs bigcache vs TinyLFU"
date: "2026-06-19"
tags: ["caching", "performance", "golang", "developer-tools", "comparison", "self-hosted", "guide", "in-memory"]
draft: false
---

## Introduction

In-memory caching is one of the most impactful performance optimizations available to self-hosted applications. Whether you are building a web server that caches database query results, a proxy that buffers API responses, or a monitoring system that aggregates metrics, an efficient caching layer can reduce response times by 10x or more.

Go (Golang) has become the dominant language for self-hosted infrastructure tools — from Traefik and Caddy to Grafana, Prometheus, and Kubernetes operators. Choosing the right in-memory cache library for your Go application directly affects garbage collection pressure, memory efficiency, and request throughput under load.

In this guide, we compare four production-tested Go cache libraries: **golang-lru** (HashiCorp's LRU cache), **go-cache** (the most popular general-purpose cache), **bigcache** (optimized for gigabytes of data), and **TinyLFU** (the academically-optimal eviction policy). Each library solves a different caching challenge, and picking the wrong one can silently degrade your application's performance.

## Why Cache Libraries Matter for Self-Hosted Services

A self-hosted API gateway might cache authentication tokens to avoid hitting the database on every request. A monitoring dashboard caches time-series query results to keep the UI responsive. A container registry caches image layer metadata to speed up pulls. These are all cases where an in-process cache, embedded directly in the application binary, outperforms external caching services like Redis or Memcached by eliminating network round-trips.

However, not all caches are equal. A naive `map[string]interface{}` with a mutex will collapse under concurrent load. A cache without an eviction policy will eventually consume all available memory. A cache that does not consider GC (garbage collection) pressure will cause stop-the-world pauses in performance-sensitive applications. The libraries below solve these problems with production-tested implementations.

## Comparison Table

| Feature | golang-lru | go-cache | bigcache | TinyLFU |
|---------|------------|----------|----------|---------|
| Stars | 5,088 | 8,827 | 8,136 | 270 |
| Eviction Policy | LRU, 2Q, ARC | TTL-based | FIFO with sharding | TinyLFU (sketch-based) |
| Concurrency | External sync | Built-in RWMutex | Lock-free sharding | Thread-safe |
| GC-Friendly | No | No | Yes (off-heap) | Moderate |
| Max Size Control | Entry count | Entry count + TTL | Byte limit | Entry count |
| License | MPL 2.0 | MIT | Apache 2.0 | MIT |
| Updated | 2026-05-25 | 2023-11-20 | 2026-04-24 | 2025-01-24 |
| Best For | Bounded-size caches | Simple TTL caching | Massive in-memory data | High hit-ratio optimization |

## golang-lru: Precision Eviction Policies from HashiCorp

[golang-lru](https://github.com/hashicorp/golang-lru) provides three cache eviction algorithms in a single library: **LRU** (Least Recently Used), **2Q** (Two-Queue LRU, which separates frequently and infrequently accessed items), and **ARC** (Adaptive Replacement Cache, which dynamically balances recency and frequency). This makes it the most algorithmically sophisticated cache in the comparison.

LRU is the simplest policy and works well when access patterns follow temporal locality (recently accessed items are likely to be accessed again). 2Q improves on LRU by protecting the cache from one-time scans that would evict frequently used entries. ARC goes further by self-tuning — it adjusts the balance between recency and frequency based on observed access patterns without any manual configuration.

```go
package main

import (
    "fmt"
    lru "github.com/hashicorp/golang-lru/v2"
)

func main() {
    // Create an LRU cache with capacity for 1000 entries
    cache, _ := lru.New[string, []byte](1000)
    
    cache.Add("user:42", []byte(`{"name": "Alice", "role": "admin"}`))
    cache.Add("session:abc123", []byte(`{"token": "eyJhbG..."}`))
    
    if val, ok := cache.Get("user:42"); ok {
        fmt.Printf("Cached user: %s\n", val)
    }
    
    // Item count is bounded — 1001st addition evicts the least recently used
    fmt.Printf("Cache size: %d\n", cache.Len())
}
```

golang-lru is used internally by HashiCorp's own tools (Consul, Vault, Nomad) and by numerous Go-based infrastructure projects. Its eviction policies are backed by academic research and refined through years of production use in distributed systems.

**Best for:** Applications where cache hit ratio is critical and access patterns are complex. Use 2Q or ARC when your cache must handle both frequent and infrequent access patterns without manual tuning.

## go-cache: The Pragmatic Drop-In Solution

[go-cache](https://github.com/patrickmn/go-cache) is the most downloaded Go cache library with 8,827 stars — a testament to its simplicity and reliability. It provides a straightforward `map[string]interface{}` style API with built-in expiration (TTL) and cleanup, making it ideal for quick integration into existing Go services.

Unlike golang-lru, go-cache does not enforce a size limit — eviction is purely time-based. This makes it suitable for caches where entries have a known lifetime (API tokens, session data, DNS records) but dangerous for unbounded datasets that could consume all available memory.

```go
package main

import (
    "fmt"
    "time"
    "github.com/patrickmn/go-cache"
)

func main() {
    // Cache with 5-minute default expiration and 10-minute cleanup interval
    c := cache.New(5*time.Minute, 10*time.Minute)
    
    // Set with explicit expiration
    c.Set("api_response", []byte(`{"status": "ok"}`), 2*time.Minute)
    
    // Set with default expiration
    c.SetDefault("config_hash", "sha256:abc123")
    
    if val, found := c.Get("api_response"); found {
        fmt.Printf("Cached: %s\n", val)
    }
    
    // Items automatically expire and are cleaned up
    fmt.Printf("Item count: %d\n", c.ItemCount())
}
```

go-cache is used in thousands of open-source and commercial Go projects. Its stability (last updated November 2023) reflects its maturity — the API has been stable for years, and there is little left to change in a well-designed TTL-based cache.

**Best for:** Simple caching needs where entries have predictable lifetimes and the cache size is naturally bounded. Session data, API response caching, DNS query results, and short-lived computation results.

## bigcache: Caching Gigabytes Without GC Pressure

[bigcache](https://github.com/allegro/bigcache) solves a uniquely Go-specific problem: garbage collection pressure. In Go, maps of `map[string][]byte` cause the GC to scan every byte slice on every collection cycle. For a cache containing millions of entries totaling multiple gigabytes, this scanning can cause multi-second "stop-the-world" pauses.

bigcache's solution is elegantly simple: store all cached data in a contiguous byte slice (a single memory allocation) and use a hash-based index to locate entries. The GC sees one large allocation instead of millions of small ones, reducing GC pause times by orders of magnitude.

```go
package main

import (
    "fmt"
    "github.com/allegro/bigcache/v3"
)

func main() {
    config := bigcache.DefaultConfig(10 * time.Minute)
    config.HardMaxCacheSize = 512 // MB
    
    cache, _ := bigcache.NewBigCache(config)
    
    cache.Set("request:a1b2c3", []byte(`{"path": "/api/data", "status": 200}`))
    cache.Set("request:d4e5f6", []byte(`{"path": "/api/users", "status": 200}`))
    
    if entry, err := cache.Get("request:a1b2c3"); err == nil {
        fmt.Printf("Cached: %s\n", entry)
    }
    
    stats := cache.Stats()
    fmt.Printf("Hits: %d, Misses: %d, Size: %d bytes\n", 
        stats.Hits, stats.Misses, cache.Len())
}
```

bigcache also shards its internal data structure (configurable shard count), eliminating lock contention under high concurrency. Each shard has its own lock, so writes to different shards proceed in parallel.

**Best for:** Go applications that need to cache large volumes of data (100MB+) in process. Proxy servers, content caches, API gateways, and any service where GC pauses would degrade latency SLAs.

## TinyLFU: Academic Cache Theory in Production

[TinyLFU](https://github.com/dgryski/go-tinylfu) implements the TinyLFU (Tiny Least Frequently Used) admission policy — a sketch-based probabilistic data structure that estimates item access frequency using minimal memory. Instead of tracking exact access counts, TinyLFU maintains a compact Count-Min Sketch that can determine whether an incoming item deserves a cache slot more than the item it would evict.

This approach is used by Caffeine (Java's highest-performance cache library, powering Cassandra and Elasticsearch) and represents the state of the art in cache eviction. The Go implementation by Damian Gryski brings this algorithm to Go applications with a clean, minimal API.

```go
package main

import (
    "fmt"
    "github.com/dgryski/go-tinylfu"
)

func main() {
    cache := tinylfu.New(1000, 100000)
    
    cache.Add("endpoint:/api/health", []byte("ok"))
    cache.Add("endpoint:/api/users", []byte(`[{"id":1}]`))
    
    if val := cache.Get("endpoint:/api/health"); val != nil {
        fmt.Printf("Cached: %s\n", val)
    }
    
    fmt.Printf("Estimator samples: %d\n", cache.Samples())
}
```

TinyLFU is a niche library — with only 270 stars — but it represents the highest-quality eviction algorithm available. For caches where hit ratio is the primary metric and you can tolerate the algorithm's memory overhead (the sketch adds ~1% additional memory), TinyLFU consistently outperforms LRU in academic benchmarks.

**Best for:** Read-heavy workloads where cache hit ratio optimization is critical. Content delivery, database query result caching, and DNS resolvers benefit most from TinyLFU's admission-based eviction.

## Choosing the Right Cache Library for Your Go Application

The decision tree is straightforward:

- **Need time-based expiration with minimal code changes?** → go-cache
- **Need bounded cache size with intelligent eviction?** → golang-lru (use ARC for self-tuning)
- **Caching gigabytes of data in process?** → bigcache (GC-friendly design)
- **Maximizing cache hit ratio for a read-heavy workload?** → TinyLFU

For most self-hosted Go applications, the combination of go-cache for simple TTL-based caching and golang-lru for size-bounded caches covers 90% of use cases. bigcache becomes important when your cache grows beyond 100MB, and TinyLFU is worth evaluating when every cache miss translates to an expensive database query or external API call.

For related reading, see our [in-memory data grid comparison](../2026-04-22-hazelcast-vs-apache-ignite-vs-infinispan-self-hosted-in-memory-data-grid-guide-2026/) for distributed caching across multiple nodes, and our [build cache comparison](../2026-04-23-sccache-vs-ccache-vs-icecream-self-hosted-build-cache-2026/) for development workflow optimization.

## FAQ

### When should I use an in-process cache instead of Redis?

Use an in-process cache when the cached data is local to a single application instance, access latency must be measured in nanoseconds (not microseconds), and the cache contents do not need to be shared across multiple services. Redis is better when multiple application instances need a shared cache, when persistence is required, or when the cache data exceeds available application memory.

### How does bigcache avoid garbage collection pressure?

bigcache allocates a single contiguous byte slice and stores all cached data within it using manual memory management. The Go garbage collector only sees a small number of large allocations, rather than millions of individual byte slices. This reduces GC scan time from seconds to milliseconds for multi-gigabyte caches.

### Will golang-lru's ARC implementation work for all access patterns?

ARC (Adaptive Replacement Cache) self-tunes based on observed access patterns, balancing between recency (LRU) and frequency (LFU). It performs well across most workloads but has higher memory overhead (~2x compared to simple LRU) because it maintains both LRU and LFU lists. For most applications, ARC's self-tuning makes it the best single-policy choice.

### Is go-cache still maintained?

go-cache reached API stability years ago and the core implementation does not require active maintenance. The library's simplicity (a single file, ~500 lines of Go) means it has few bugs to fix. It is used in thousands of production Go applications and is considered stable. For new features beyond TTL-based caching, consider golang-lru or bigcache.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted In-Memory Cache Libraries: golang-lru vs go-cache vs bigcache vs TinyLFU",
  "description": "Compare Go in-memory cache libraries for self-hosted applications: HashiCorp golang-lru (LRU/2Q/ARC), go-cache (TTL-based), bigcache (GC-friendly gigabyte-scale), and TinyLFU (probabilistic admission). Code examples and selection guide.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
