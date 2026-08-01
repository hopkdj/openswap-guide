---
title: "C# In-Memory Caching Libraries: MemoryCache vs LazyCache vs FusionCache — Choosing the Right Cache Strategy for .NET"
date: "2026-08-02"
tags: ["csharp", "dotnet", "caching", "performance", "in-memory-cache", "fusioncache", "lazycache"]
draft: false
---

## Introduction

Caching is one of the most effective ways to improve application performance — a well-placed cache can reduce database load by 90% or more while cutting response times from hundreds of milliseconds to microseconds. In the .NET ecosystem, developers have three tiers of in-memory caching libraries to choose from: the built-in **MemoryCache**, the lightweight wrapper **LazyCache** (1,756 GitHub stars), and the feature-rich hybrid **FusionCache** (3,850 stars).

Each library targets a different level of complexity. This guide compares their APIs, features, and trade-offs to help you pick the right caching strategy for your .NET application.

## Comparison Table

| Feature | MemoryCache | LazyCache | FusionCache |
|---------|-------------|-----------|-------------|
| **GitHub Stars** | Built-in (.NET) | 1,756 | 3,850 |
| **Last Updated** | August 2026 (runtime) | October 2025 | July 2026 |
| **Thread Safety** | Yes | Yes | Yes |
| **Lazy Initialization** | Manual | Automatic (`GetOrAdd`) | Automatic (`GetOrSet`) |
| **Distributed Cache** | No | No | Plugin (Redis, Memcached) |
| **Cache Stampede Protection** | No | No | Yes (built-in) |
| **Fail-Safe / Resilience** | No | No | Yes (stale data fallback) |
| **Backplane Support** | No | No | Yes |
| **Expiration Types** | Absolute, Sliding | Absolute, Sliding | Absolute, Sliding, Hybrid |
| **NuGet Package** | `Microsoft.Extensions.Caching.Memory` | `LazyCache` | `ZiggyCreatures.FusionCache` |
| **Serializer Support** | N/A (in-memory only) | N/A | Custom serializers |

## MemoryCache: The Built-In Foundation

`IMemoryCache` is included in `Microsoft.Extensions.Caching.Memory` and provides a thread-safe, key-value store with automatic expiration. It's the foundation that both LazyCache and FusionCache build upon.

### Installation

```bash
dotnet add package Microsoft.Extensions.Caching.Memory
```

### Basic Usage

```csharp
using Microsoft.Extensions.Caching.Memory;

// Register in DI
builder.Services.AddMemoryCache();

// Inject and use
public class ProductService
{
    private readonly IMemoryCache _cache;

    public ProductService(IMemoryCache cache) => _cache = cache;

    public async Task<Product?> GetProductAsync(int id)
    {
        var key = $"product_{id}";

        if (!_cache.TryGetValue(key, out Product? product))
        {
            product = await _db.Products.FindAsync(id);
            if (product != null)
            {
                _cache.Set(key, product, TimeSpan.FromMinutes(10));
            }
        }

        return product;
    }
}
```

MemoryCache requires manual cache-miss handling — the "check, fetch, store" pattern shown above. While straightforward, this pattern introduces a race condition under concurrent load: two threads can both miss the cache simultaneously, both query the database, and both write back. This is the classic **cache stampede** problem.

### Advanced Configuration

```csharp
builder.Services.AddMemoryCache(options =>
{
    options.SizeLimit = 1024; // Max cache entries
    options.CompactionPercentage = 0.25;
    options.ExpirationScanFrequency = TimeSpan.FromMinutes(1);
});

// Size-aware caching
var options = new MemoryCacheEntryOptions()
    .SetAbsoluteExpiration(TimeSpan.FromHours(1))
    .SetSlidingExpiration(TimeSpan.FromMinutes(10))
    .SetSize(1) // Each entry counts as 1 unit
    .SetPriority(CacheItemPriority.Normal);

_cache.Set(key, data, options);
```

## LazyCache: The Ergonomic Wrapper

LazyCache wraps `IMemoryCache` with a fluent, lambda-based API that eliminates the manual check-fetch-store pattern. Its `GetOrAdd()` method accepts a factory function and handles the caching logic transparently.

### Installation

```bash
dotnet add package LazyCache
```

### Basic Usage

```csharp
using LazyCache;

// Register
builder.Services.AddLazyCache();

// Inject and use
public class ProductService
{
    private readonly IAppCache _cache;

    public ProductService(IAppCache cache) => _cache = cache;

    public async Task<Product?> GetProductAsync(int id)
    {
        return await _cache.GetOrAddAsync(
            $"product_{id}",
            async () => await _db.Products.FindAsync(id),
            DateTimeOffset.Now.AddMinutes(10)
        );
    }
}
```

The `GetOrAddAsync` method handles the entire caching lifecycle: check the cache, call the factory on miss, store the result, and return it. The code is significantly cleaner than the raw `MemoryCache` equivalent.

### Default Expiration Policy

```csharp
// Set default expiration for all cache entries
builder.Services.AddLazyCache(options =>
{
    options.DefaultCacheDurationSeconds = 300; // 5 minutes
});
```

### Cache Invalidation

```csharp
_cache.Remove($"product_{productId}");
_cache.RemoveByPrefix("product_"); // Remove all product entries
```

## FusionCache: The Production-Grade Powerhouse

FusionCache is the most sophisticated option, designed for high-availability scenarios. It addresses cache stampede, provides fail-safe fallback to stale data, supports distributed backplanes, and offers a hybrid in-memory + distributed architecture.

### Installation

```bash
dotnet add package ZiggyCreatures.FusionCache
dotnet add package ZiggyCreatures.FusionCache.Serialization.SystemTextJson
```

### Basic Usage

```csharp
using ZiggyCreatures.FusionCache;

// Register
builder.Services.AddFusionCache();

// Inject and use
public class ProductService
{
    private readonly IFusionCache _cache;

    public ProductService(IFusionCache cache) => _cache = cache;

    public async Task<Product?> GetProductAsync(int id)
    {
        return await _cache.GetOrSetAsync<Product>(
            $"product_{id}",
            async (ctx, ct) => await _db.Products.FindAsync(id),
            options => options
                .SetDuration(TimeSpan.FromMinutes(10))
                .SetFailSafe(true, TimeSpan.FromHours(2)) // Serve stale data on failure
                .SetFactoryTimeouts(TimeSpan.FromSeconds(5))
        );
    }
}
```

### Cache Stampede Protection

FusionCache's most valuable feature is automatic cache stampede prevention. When multiple concurrent requests miss the cache for the same key, only one factory executes — all others wait for and reuse its result:

```csharp
// No special config needed — built-in behavior
await _cache.GetOrSetAsync<Product>(
    "hot-item",
    async (ctx, ct) => await ExpensiveDbQueryAsync(),
    options => options.SetDuration(TimeSpan.FromMinutes(5))
);
```

### Distributed Cache with Redis

```bash
dotnet add package ZiggyCreatures.FusionCache.Backplane.StackExchangeRedis
```

```csharp
builder.Services.AddFusionCache()
    .WithDefaultEntryOptions(new FusionCacheEntryOptions
    {
        Duration = TimeSpan.FromMinutes(10),
        IsFailSafeEnabled = true,
        FailSafeMaxDuration = TimeSpan.FromHours(2)
    })
    .WithSerializer(new FusionCacheSystemTextJsonSerializer())
    .WithDistributedCache(
        new RedisCache(new RedisCacheOptions
        {
            Configuration = "localhost:6379"
        })
    )
    .WithBackplane(
        new RedisBackplane(new RedisBackplaneOptions
        {
            Configuration = "localhost:6379"
        })
    );
```

### Fail-Safe Mode in Action

When the database is down, FusionCache can serve stale cached data instead of throwing exceptions:

```csharp
// If factory throws, FusionCache returns expired (but still cached) data
// if FailSafe is enabled (see config above).
var product = await _cache.GetOrSetAsync<Product>(
    $"product_{id}",
    async (ctx, ct) => await _db.Products.FindAsync(id)
);
// product may be stale but not null — keeps your app running
```

## Deployment Architecture

When integrating caching into your application, consider these architectural patterns:

**Single-instance applications** can use any of the three libraries with in-memory caching alone. MemoryCache or LazyCache are sufficient and simpler to maintain.

**Multi-instance (load-balanced) deployments** need cache synchronization to avoid inconsistencies where instance A has fresh data but instance B serves stale data from its local cache. FusionCache with a Redis backplane solves this automatically — cache evictions on one instance propagate to all others.

**High-availability scenarios** benefit most from FusionCache's fail-safe mode. If your database experiences a temporary outage, FusionCache continues serving cached data rather than returning errors to users. This can be the difference between a minor blip and a full outage from the user's perspective.

## Why Your Caching Strategy Matters

Caching is one of those cross-cutting concerns that's easy to get wrong. A naive implementation introduces cache stampede under load, serves stale data after updates, or fails entirely when the backing store goes down. The right library handles these edge cases transparently. For a broader perspective on in-memory data handling, see our [in-memory data grid comparison](../2026-04-22-hazelcast-vs-apache-ignite-vs-infinispan-self-hosted-in-memory-data-grid-guide-2026/). If you're working with Python caching as well, our [Python caching libraries guide](../2026-06-22-python-caching-libraries-cachetools-diskcache-dogpile-guide/) covers the equivalent ecosystem. For understanding how caching fits into your dependency injection setup, check our [C# DI containers comparison](../2026-07-04-csharp-di-containers-autofac-ninject-castle-windsor-simpleinjector-lamar/).
## Migration and Coexistence Strategies

It's common for .NET projects to start with MemoryCache and later need the advanced features of FusionCache. Here's how to handle each migration path.

**From MemoryCache to LazyCache** is the simplest upgrade — LazyCache wraps `IMemoryCache` directly, so all existing cache entries remain accessible. Replace `TryGetValue` / `Set` pairs with `GetOrAddAsync` calls, which typically cuts caching-related code by half. Your DI registration changes from `AddMemoryCache()` to `AddLazyCache()` in a single line.

**From LazyCache to FusionCache** requires a bit more work but unlocks distributed caching and fail-safe capabilities. The API is similar — `GetOrAdd` becomes `GetOrSet` — but FusionCache adds explicit options configuration for each call. Plan for a phased migration: deploy FusionCache alongside LazyCache, migrate hot-path caches first, and monitor cache hit rates to verify no regression.

**Coexistence** is fully supported — all three libraries can run simultaneously in the same application. This is useful during migrations where some services still depend on the legacy cache while new features leverage FusionCache's advanced capabilities. Just register each with a different DI interface (`IMemoryCache`, `IAppCache`, `IFusionCache`) to avoid conflicts.

For teams considering a Redis-backed distributed cache: start with FusionCache in in-memory-only mode, then add the Redis backplane when you're confident in the caching logic. The code change is minimal — just add `.WithDistributedCache()` configuration — and FusionCache handles the synchronization transparently.

## FAQ

### Can I use FusionCache with LazyCache in the same project?

Technically yes, but there's no reason to. FusionCache includes all the ergonomic features of LazyCache (factory-based `GetOrSet`) plus advanced capabilities. Using both adds unnecessary dependency overhead without benefit.

### How does cache stampede protection work in FusionCache?

When multiple concurrent requests miss the cache for the same key, FusionCache creates a single lock for that key. Only the first request executes the factory function. All other requests wait (with a configurable timeout) and receive the same result once the factory completes. This prevents thundering-herd scenarios where dozens of identical database queries fire simultaneously.

### What happens to cached data when the application restarts?

All three libraries store data in-memory only by default, so cached data is lost on restart. If persistence across restarts is required, use FusionCache with a distributed cache backend (Redis, SQL Server) configured as a secondary storage layer. FusionCache automatically falls back to the distributed cache when the in-memory cache is cold.

### Does MemoryCache support cancellation tokens?

Yes. `MemoryCacheEntryOptions` accepts `ExpirationTokens` and `PostEvictionCallbacks` that integrate with `CancellationToken`:

```csharp
var cts = new CancellationTokenSource();
options.AddExpirationToken(new CancellationChangeToken(cts.Token));
```

When the token is cancelled (e.g., a configuration change), the cache entry is evicted automatically.

### How do I monitor cache hit rates?

FusionCache provides built-in events for cache hits, misses, and factory calls. Wire them up in your startup:

```csharp
_cache.Events.Hit += (sender, args) => Console.WriteLine($"Hit: {args.Key}");
_cache.Events.Miss += (sender, args) => Console.WriteLine($"Miss: {args.Key}");
_cache.Events.FactorySuccess += (sender, args) =>
    Console.WriteLine($"Factory completed: {args.Key}");
```

For MemoryCache and LazyCache, you'll need to wrap calls with your own instrumentation using a custom cache wrapper or a delegating handler pattern.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C# In-Memory Caching Libraries: MemoryCache vs LazyCache vs FusionCache — Choosing the Right Cache Strategy for .NET",
  "description": "Detailed comparison of .NET in-memory caching libraries: MemoryCache, LazyCache, and FusionCache. Covers cache stampede protection, fail-safe patterns, Redis backplane integration, and deployment architecture.",
  "datePublished": "2026-08-02",
  "dateModified": "2026-08-02",
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
