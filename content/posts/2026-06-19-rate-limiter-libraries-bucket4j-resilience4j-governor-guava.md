---
title: "Self-Hosted Rate Limiter Libraries: Bucket4j vs Resilience4j vs Governor vs Guava RateLimiter"
date: "2026-06-19"
tags: ["rate-limiting", "java-libraries", "rust-libraries", "api-design", "traffic-management", "fault-tolerance"]
draft: false
---

Every API needs rate limiting. Whether protecting against abuse, enforcing tiered pricing, or preventing cascading failures, rate limiters are the first line of defense for service reliability. While reverse proxies like Nginx and Envoy provide server-level rate limiting, application-level rate limiter libraries give developers fine-grained control — per-user quotas, dynamic limits, distributed coordination, and custom rejection strategies.

This article compares four production-grade rate limiter libraries: **Bucket4j** (Java), **Resilience4j RateLimiter** (Java), **Governor** (Rust), and **Google Guava RateLimiter** (Java). Each implements the token bucket algorithm — the industry standard for burst-tolerant rate limiting — with different features and trade-offs.

## Why Application-Level Rate Limiting?

Server-level rate limiting (Nginx `limit_req`, Envoy rate limit filter, HAProxy stick tables) operates at the connection or request level. It's great for protecting infrastructure but limited in what it can express: you can't easily implement "free users get 100 requests/day, pro users get 10,000" at the proxy layer.

Application-level rate limiter libraries solve this by embedding rate limiting logic directly in your service code. Benefits include:

- **Per-resource granularity**: Limit `/api/sensitive` to 10 req/min while allowing 1000 req/min on `/api/public`
- **User-aware quotas**: Tie limits to account tiers, API keys, or OAuth scopes
- **Distributed coordination**: Share rate limit state across multiple service instances via Redis or similar
- **Custom rejection handling**: Return JSON error responses, trigger webhooks, or queue requests instead of blocking
- **Business logic integration**: Deduct from a user's monthly quota atomically, or apply different limits during business hours

## Comparison Table

| Feature | Bucket4j | Resilience4j | Governor | Guava RateLimiter |
|---------|----------|--------------|----------|-------------------|
| Language | Java | Java | Rust | Java |
| GitHub Stars | 2,760 | 10,691 | 918 | 50,000+ (Guava) |
| Algorithm | Token Bucket | Token Bucket | Token Bucket / GCRA | Smooth Bursty / Warming Up |
| Distributed Support | Yes (Redis, Hazelcast, etc.) | No (local only) | No (local only) | No (local only) |
| Dynamic Limits | Yes | Yes | Via middleware | No (fixed at creation) |
| Burst Handling | Configurable burst | Configurable burst | Configurable burst | Smooth burst / warming up |
| Blocking Wait | Yes | No (non-blocking only) | Yes (via Tower) | Yes (`acquire()`) |
| Metrics/Monitoring | Yes | Yes (Micrometer) | No built-in | No |
| Last Updated | 2026-05-20 | 2026-06-16 | 2026-02-09 | 2026-05-01 |
| License | Apache-2.0 | Apache-2.0 | MIT | Apache-2.0 |

## Bucket4j: Full-Featured Distributed Rate Limiting

[Bucket4j](https://github.com/bucket4j/bucket4j) is the most feature-complete rate limiting library in the Java ecosystem. It implements the token bucket algorithm with support for local, distributed (Redis, Hazelcast, Ignite, Coherence, Infinispan), and clustered backends.

```java
import io.github.bucket4j.Bucket;
import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Refill;
import java.time.Duration;

// Create a rate limiter: 100 tokens per minute, with burst of 20
Bandwidth limit = Bandwidth.classic(100, Refill.greedy(100, Duration.ofMinutes(1)));
Bucket bucket = Bucket.builder()
    .addLimit(limit)
    .build();

// Try to consume a token
if (bucket.tryConsume(1)) {
    processRequest();
} else {
    throw new RateLimitExceededException("Too many requests");
}

// Distributed mode with Redis
// Bucket bucket = Bucket.builder()
//     .addLimit(limit)
//     .build(redisProxy, "user:" + userId);
```

Bucket4j supports multiple bandwidth definitions per bucket (e.g., "100 per minute AND 1000 per hour"), greedy and interval-based refill strategies, and both blocking and non-blocking consumption. The `tryConsumeAndReturnRemaining()` method returns the remaining tokens, useful for adding `X-RateLimit-Remaining` headers.

**Key strengths**: Distributed rate limiting out of the box, multiple backend support, per-bucket multiple limits, comprehensive API for token inspection, actively maintained.

**Limitations**: Java-only, the distributed backends add operational complexity (you need to run Redis, Hazelcast, etc.), slightly more verbose API compared to simpler alternatives.

## Resilience4j RateLimiter: Fault Tolerance Ecosystem

[Resilience4j](https://github.com/resilience4j/resilience4j) is a comprehensive fault tolerance library inspired by Netflix Hystrix. Its RateLimiter module integrates seamlessly with other Resilience4j components: CircuitBreaker, Retry, Bulkhead, and TimeLimiter.

```java
import io.github.resilience4j.ratelimiter.RateLimiter;
import io.github.resilience4j.ratelimiter.RateLimiterConfig;
import java.time.Duration;

// Configure: 10 requests per second, 5 second timeout for waiting
RateLimiterConfig config = RateLimiterConfig.custom()
    .limitRefreshPeriod(Duration.ofSeconds(1))
    .limitForPeriod(10)
    .timeoutDuration(Duration.ofSeconds(5))
    .build();

RateLimiter rateLimiter = RateLimiter.of("myService", config);

// Decorate a function with rate limiting
Supplier<String> decorated = RateLimiter.decorateSupplier(rateLimiter, () -> callService());

// Or use it imperatively
if (rateLimiter.acquirePermission()) {
    callService();
} else {
    throw new RequestNotPermitted("Rate limit exceeded");
}
```

The real power of Resilience4j comes from composition: you can wrap a service call with RateLimiter → CircuitBreaker → Retry in a single decorator chain. When the rate limiter rejects a request, the circuit breaker counts the failure, and the retry mechanism backs off appropriately.

```java
// Compose multiple resilience patterns
Supplier<String> resilient = Decorators.ofSupplier(() -> callService())
    .withRateLimiter(rateLimiter)
    .withCircuitBreaker(circuitBreaker)
    .withRetry(retry)
    .decorate();
```

**Key strengths**: Part of a complete fault tolerance ecosystem, excellent Micrometer metrics integration, Spring Boot auto-configuration, well-documented resilience patterns, non-blocking design (no thread blocking).

**Limitations**: Local-only (no distributed rate limiting), no blocking `acquire()` method (must poll or fail-fast), rate limit refresh uses fixed windows internally.

## Governor: Rust's Rate Limiting Powerhouse

[Governor](https://github.com/boinkor-net/governor) (formerly `ratelimit_meter`) is the leading rate limiting library for Rust. It implements multiple algorithms including the Generic Cell Rate Algorithm (GCRA) — a more precise variant of token bucket — and supports both in-memory and pluggable state storage.

```rust
use governor::{Quota, RateLimiter};
use std::num::NonZeroU32;
use std::time::Duration;

// Allow 5 requests per second with burst capacity of 3
let limiter = RateLimiter::direct(
    Quota::per_second(NonZeroU32::new(5).unwrap())
        .allow_burst(NonZeroU32::new(3).unwrap())
);

// Non-blocking check
if limiter.check().is_ok() {
    handle_request();
} else {
    return Err("Rate limit exceeded");
}

// With Tower middleware (Axum/Actix-web/Tonic)
use tower_governor::{GovernorLayer, GovernorConfig};

let config = GovernorConfig {
    per_second: 5,
    burst_size: 10,
    key_extractor: tower_governor::key_extractor::SmartIpKeyExtractor,
    ..Default::default()
};

// Add to your Axum router
let app = Router::new()
    .route("/api", get(handler))
    .layer(GovernorLayer {
        config: Box::new(config),
    });
```

Governor shines in Rust web services through its Tower middleware integration. With one import, you get per-IP rate limiting for Axum, Actix-web, or Tonic (gRPC). The `SmartIpKeyExtractor` handles X-Forwarded-For headers correctly for services behind reverse proxies.

**Key strengths**: Multiple algorithm support (token bucket + GCRA), excellent Tower/Axum integration, type-safe API leveraging Rust's ownership model, zero-cost abstractions (no runtime overhead beyond the algorithm itself), `no_std` compatible.

**Limitations**: Local-only by default (though the `KeyableStateStore` trait allows custom backends), smaller community than Java alternatives, no built-in metrics export.

## Guava RateLimiter: Google's Smooth Approach

[Google Guava's RateLimiter](https://github.com/google/guava) takes a different approach from the classic token bucket. It provides two modes: **SmoothBursty** (allows bursts of accumulated permits) and **SmoothWarmingUp** (gradually increases the permitted rate, useful for cold-start services).

```java
import com.google.common.util.concurrent.RateLimiter;

// SmoothBursty: 5 permits per second, with burst capacity
RateLimiter burstyLimiter = RateLimiter.create(5.0);

// SmoothWarmingUp: starts cold (2.5/sec) and warms up to 5/sec over 3 seconds
RateLimiter warmupLimiter = RateLimiter.create(5.0, 3.0, TimeUnit.SECONDS);

// Blocking acquire — waits if necessary
double waitTime = burstyLimiter.acquire(); // blocks until a permit is available
processRequest();

// Non-blocking tryAcquire
if (burstyLimiter.tryAcquire(1, 500, TimeUnit.MILLISECONDS)) {
    processRequest();
} else {
    handleRateLimitExceeded();
}
```

Guava's RateLimiter is deliberately simple: create it with a rate, call `acquire()` or `tryAcquire()`. No configuration classes, no decorator chains, no YAML files. The smooth warming-up mode is unique — it prevents a "cold" service from being overwhelmed by a burst of traffic after startup.

**Key strengths**: Dead simple API, unique warming-up mode, battle-tested at Google scale, zero external dependencies beyond Guava itself, excellent documentation.

**Limitations**: Fixed rate at creation time (no dynamic adjustment), local-only, no metrics or monitoring hooks, less flexible than Bucket4j for complex rate limiting scenarios, Java-only.

## Choosing the Right Rate Limiter

The right choice depends on your architecture:

- **Distributed microservices (Java)**: **Bucket4j** with Redis backend. It's the only option that handles distributed rate limiting natively, and the multiple-bandwidth feature maps well to tiered API pricing.

- **Fault-tolerant Java services**: **Resilience4j** when you're already using CircuitBreaker and Retry. The integrated decorator pattern lets you compose rate limiting with other resilience strategies. Its Micrometer integration means rate limit metrics appear in your existing dashboards.

- **Rust web services**: **Governor** with Tower middleware. The Axum/Actix-web integration is seamless, and the GCRA algorithm provides more precise rate control than simple token bucket implementations.

- **Simple Java applications**: **Guava RateLimiter** when you need basic rate limiting without external infrastructure. If you already depend on Guava (and most Java projects do), RateLimiter adds zero new dependencies.

## Implementation Patterns

**Distributed rate limiting with Bucket4j and Redis:**

```java
// Shared Redis proxy for cluster-wide rate limiting
RedisClient redisClient = RedisClient.create("redis://localhost:6379");
RedisProxy<String> proxy = RedisProxyManager
    .builder(redisClient)
    .build()
    .proxy("rate-limits");

// Each user gets their own bucket, shared across all instances
String userId = request.getUserId();
Bucket userBucket = Bucket.builder()
    .addLimit(Bandwidth.classic(1000, Refill.greedy(1000, Duration.ofHours(1))))
    .build(proxy, userId);

if (!userBucket.tryConsume(1)) {
    response.setStatus(429);
    response.setHeader("Retry-After", "3600");
    return;
}
```

**Dynamic rate limits with Resilience4j:**

```java
// Adjust limits based on user tier
RateLimiterConfig config = RateLimiterConfig.from(loadConfig(userTier))
    .get();
RateLimiter rateLimiter = RateLimiter.of("api-" + userId, config);

// Or update at runtime
rateLimiter.changeLimitForPeriod(updatedLimit);
```

For more on server-level rate limiting strategies, see our [Nginx vs Caddy vs Envoy rate limiting guide](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide-202/). For traffic management at the proxy layer, our [advanced load balancer middleware guide](../2026-05-03-self-hosted-load-balancer-advanced-haproxy-lua-traefik-middleware-envoy-wasm/) covers complementary patterns.

## FAQ

### What's the difference between token bucket and fixed window rate limiting?

Token bucket allows bursts: if you have a limit of 100 req/min with burst of 20, you can make 120 requests in the first second, then 100/min thereafter. Fixed window limits strictly to 100 per minute regardless of burst. Token bucket is more forgiving for real-world traffic patterns where clients naturally batch requests. All four libraries here use token bucket or GCRA (a variant).

### Can I use these libraries for outbound rate limiting (controlling requests my service makes to external APIs)?

Yes. All four libraries support this pattern — create a rate limiter and call `tryConsume()` or `check()` before making an outbound request. This is especially important for respecting third-party API rate limits and avoiding being banned. Bucket4j and Governor handle this well; simply create a limiter per external service and check before each outbound call.

### Do these libraries work with reactive/async frameworks?

Resilience4j has first-class support for Project Reactor and RxJava. Governor works natively with async Rust (Tokio) through Tower middleware. Bucket4j provides async support through its `AsyncBucket` variants. Guava RateLimiter is synchronous only — wrap `acquire()` in `CompletableFuture.supplyAsync()` if you need async behavior.

### How do I expose rate limit status headers (X-RateLimit-Remaining, etc.) to API consumers?

Bucket4j provides `tryConsumeAndReturnRemaining()` which returns `ConsumptionProbe` with `getRemainingTokens()`. Resilience4j exposes metrics via Micrometer that you can read and add to response headers. Governor's `check()` returns a result you can inspect for quota. Guava RateLimiter does not expose remaining tokens or quota information — for API-facing headers, prefer Bucket4j or Resilience4j.

### What happens when the rate limiter state server (Redis) goes down in a Bucket4j distributed setup?

Bucket4j's distributed proxies handle this differently depending on configuration. With `RedisProxyManager`, if Redis is unavailable, `tryConsume()` throws an exception. You can configure a fallback to local-only rate limiting or fail-open (allow requests). The recommended pattern is to use a circuit breaker (e.g., Resilience4j CircuitBreaker) around the rate limiter call and fall back to a local Bucket4j instance with a more conservative limit.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Rate Limiter Libraries: Bucket4j vs Resilience4j vs Governor vs Guava RateLimiter",
  "description": "Detailed comparison of rate limiter libraries: Bucket4j, Resilience4j RateLimiter, Governor (Rust), and Guava RateLimiter. Includes distributed rate limiting patterns, code examples, and selection guidance for API traffic management.",
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
