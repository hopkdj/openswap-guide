---
title: "Go Rate Limiting in 2026: x/time/rate vs uber-go/ratelimit vs gobreaker"
date: "2026-09-02"
tags: ["go", "rate-limiting", "circuit-breaker", "libraries", "developer-tools"]
draft: false
---

Your Go service is one traffic spike away from a cascade failure. Rate limiting is the cheapest insurance you can add, yet most teams bolt it on wrong: they pick a library by GitHub stars, add it to one handler, and discover during an incident that it only works per-process, or that it blocks forever, or that it protects against the wrong failure mode entirely. In 2026 the Go ecosystem has three serious primitives — **`golang.org/x/time/rate`** (token bucket), **`go.uber.org/ratelimit`** (leaky bucket), and **`sony/gobreaker`** (circuit breaker) — and they solve different problems.

## TL;DR: Quick Verdict

If you need **per-user or per-route limits with burst support and context cancellation**, use `x/time/rate` — it is the standard, and its `Wait`/`Allow`/`Reserve` trio covers every sane API shape. If you need a **hard, absolute ceiling on requests per second with the lowest possible overhead**, use `uber-go/ratelimit` — its blocking `Take()` is one atomic operation. If your problem is **downstream failures, not traffic volume** — a third-party API that returns 500s — you need `gobreaker`, not a rate limiter. Most production services should combine `x/time/rate` (inbound) with `gobreaker` (outbound). They are complements, not competitors.

## Head-to-Head Comparison

| Dimension | golang.org/x/time/rate | go.uber.org/ratelimit | sony/gobreaker |
|---|---|---|---|
| Pattern | Token bucket | Leaky bucket | Circuit breaker (state machine) |
| Core API | `NewLimiter`, `Wait`, `Allow`, `Reserve` | `New`, `Take` | `NewCircuitBreaker`, `Execute` |
| Blocking vs dropping | Both (`Wait` blocks, `Allow` drops) | Always blocks until slot free | Fails fast when circuit open |
| Burst support | Yes, explicit `burst` parameter | No (fixed per-second) | N/A |
| Context cancellation | Full `context.Context` support | Not supported | Not supported |
| Overhead | Moderate (mutex + timer) | Minimal (atomics only) | Low (atomic counters) |
| Rolling window stats | No | No | Yes (`Counts`, `BucketPeriod`) |
| License | BSD-3-Clause | MIT | MIT |
| GitHub stars (2026-09) | 422 (mirror repo) | 4,714 | 3,692 |
| Last push | 2026-08-19 | 2024-05-01 | 2026-02-07 |

## Use Case Decision Matrix

| Use Case | Recommended Tool | Why |
|---|---|---|
| Per-IP / per-user API limits with burst headroom | x/time/rate | `burst` parameter + `Allow()` for cheap rejection |
| Absolute QPS ceiling for a hot path | uber-go/ratelimit | Fastest path to "never exceed N requests/sec" |
| Protecting calls to a flaky third-party API | gobreaker | Trips on failure ratio, not on volume |
| HTTP handler middleware | x/time/rate | `Wait(ctx)` integrates with request context deadlines |
| Full microservice resilience (inbound + outbound) | x/time/rate + gobreaker | Rate-limit inbound, break outbound circuits |
| Zero-dependency, single-machine worker loop | uber-go/ratelimit | One import, one line, no timers to leak |

## x/time/rate: The Standard Token Bucket

`golang.org/x/time/rate` (part of the `golang/time` repo, updated August 2026) is the de facto standard for rate limiting in Go. Its `Limiter` controls the rate of events using a token bucket: the bucket holds at most `burst` tokens and refills at `rate` tokens per second. `NewLimiter(r Limit, b int)` creates one, and the real API surface from the source is:

```go
import (
    "context"
    "net/http"

    "golang.org/x/time/rate"
)

// 10 events per second, burst of 30
limiter := rate.NewLimiter(rate.Limit(10), 30)

func handler(w http.ResponseWriter, r *http.Request) {
    // Blocking variant: wait until a token is available,
    // or until the request's context deadline fires.
    if err := limiter.Wait(r.Context()); err != nil {
        http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
        return
    }

    // Non-blocking variant: drop excess requests immediately.
    // if !limiter.Allow() {
    //     http.Error(w, "rate limit exceeded", http.StatusTooManyRequests)
    //     return
    // }
}
```

The third method, `Reserve`, returns a `Reservation` you can `Delay()` or `Cancel()` — useful for queue-based workers. Because `Wait` honors context cancellation, it composes cleanly with `http.Server` timeouts and `context.WithTimeout`. The one thing it is not: a distributed limiter. Every `Limiter` instance holds its own bucket, so you need one limiter per key (IP, user ID, API key) and, for multi-instance deployments, a shared store on top.

## uber-go/ratelimit: The Leaky Bucket at Warp Speed

`go.uber.org/ratelimit` (4,714 stars) implements the leaky bucket: a fixed number of operations per second, refilled based on elapsed time between requests rather than a clock tick. The API is a single method — `Take()` blocks until you are allowed to proceed. The README's canonical example is the whole tutorial:

```go
import (
    "fmt"
    "time"

    "go.uber.org/ratelimit"
)

func main() {
    rl := ratelimit.New(100) // per second

    prev := time.Now()
    for i := 0; i < 10; i++ {
        now := rl.Take()
        fmt.Println(i, now.Sub(prev))
        prev = now
    }

    // Output:
    // 0 0
    // 1 10ms
    // 2 10ms
    // 3 10ms
}
```

Every `Take()` spacing out to exactly 10ms shows the design goal: a hard, even ceiling on throughput with near-zero overhead (the hot path is atomic operations, no timers, no goroutines). The trade-offs: no burst support, no context cancellation, and the README itself points to `x/time/rate` for "more complex use-cases". The project's last push was May 2024 — it is stable and finished rather than abandoned, but don't expect new features. Use it in tight loops and worker pools where you know the rate you want and want nothing else.

## gobreaker: The Circuit Breaker You Actually Meant to Add

`song/gobreaker` (3,692 stars, updated February 2026) implements the circuit breaker pattern: a state machine that goes **closed → open → half-open** based on failure counts, and fails fast while open. It is not a rate limiter — it protects against downstream *failure*, not upstream *volume* — which is why it belongs next to, not instead of, the other two. The modern API uses generics:

```go
import "github.com/sony/gobreaker/v2"

cb := gobreaker.NewCircuitBreaker[any](gobreaker.Settings{
    Name: "payments-api",
    ReadyToTrip: func(counts gobreaker.Counts) bool {
        failureRatio := float64(counts.ConsecutiveFailures) / float64(counts.Requests)
        return counts.Requests >= 3 && failureRatio >= 0.6
    },
})

resp, err := cb.Execute(func() (interface{}, error) {
    return callPaymentsAPI() // the call that might fail
})
if err != nil {
    // circuit open or call failed — degrade gracefully
}
```

The `Settings` struct gives you real control: `MaxRequests` (half-open probes), `Interval` and `BucketPeriod` (rolling window vs fixed window), `Timeout` (default 60s in open state), `ReadyToTrip`, `OnStateChange`, and — useful in practice — `IsExcluded` for errors like context cancellation that should not count against the circuit. `v2` with generics means no more `interface{}` casts on your result type. This is the tool for the "third-party API is on fire" scenario, where a rate limiter would keep sending requests into the fire.

## Pitfalls: Five Ways Go Rate Limiting Goes Wrong

1. **Per-instance limiters are not distributed limits.** `x/time/rate` and `uber-go/ratelimit` both keep state in memory. Run 5 replicas behind a load balancer and each allows the full rate — 5x the intended load. For real API limits you need a shared counter (Redis, etc.) or a gateway-level limiter; see our [platform-level rate limiting guide](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide-2026/) for the proxy-side approach.
2. **`Take()` blocks forever without a timeout.** If your worker calls `Take()` and the rate is exhausted, it sleeps until the next slot. In an HTTP handler that's a hang; wrap it in a goroutine with `select` and a timeout, or use `x/time/rate`'s context-aware `Wait` instead.
3. **`NewLimiter(rate, 0)` silently allows nothing.** The bucket starts with `burst` tokens, so a burst of 0 means `Allow()` always returns false. This produces "everything is 429" incidents that look like an outage. Always set burst ≥ 1, and test with `limiter.Tokens()`.
4. **Rate limiting and circuit breaking are different defenses.** A rate limiter controls how much you *send*; a circuit breaker stops you when the *receiver* is unhealthy. Using only one leaves the other hole open. The [cross-language circuit breaker comparison](../2026-06-21-circuit-breaker-libraries-resilience4j-hystrix-failsafe-go-polly/) covers the pattern in depth if you are choosing between implementations.
5. **Default settings are for demos, not production.** gobreaker's default `ReadyToTrip` trips after 5 consecutive failures — fine for a demo, too slow for a dependency that must fail fast. `uber-go/ratelimit`'s fixed window means no burst headroom at all — spikes get flattened into latency. Tune every parameter against your actual traffic shape, and record `OnStateChange` events to your metrics pipeline so you can see circuits trip.

## JSON-LD Structured Data

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Rate Limiting in 2026: x/time/rate vs uber-go/ratelimit vs gobreaker",
  "description": "Deep comparison of Go's three rate limiting and resilience primitives: golang.org/x/time/rate (token bucket), go.uber.org/ratelimit (leaky bucket), and sony/gobreaker (circuit breaker). Real code, live star counts, and a use-case decision matrix.",
  "datePublished": "2026-09-02",
  "dateModified": "2026-09-02",
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

### What is the difference between a token bucket and a leaky bucket?

A token bucket allows bursts: the bucket accumulates tokens up to a `burst` size, so short spikes pass while the average rate stays bounded. A leaky bucket enforces a perfectly even rate — requests are spaced out to exactly the configured interval. `x/time/rate` is a token bucket; `uber-go/ratelimit` is a leaky bucket.

### Does golang.org/x/time/rate work across multiple server instances?

No. Each `Limiter` instance tracks its own tokens in memory. For multi-instance deployments you must either shard by key with a shared state store (Redis-based counters) or move rate limiting to the gateway/proxy layer.

### When should I use a circuit breaker instead of a rate limiter?

When the problem is downstream health, not traffic volume. If a third-party API starts returning 500s, a rate limiter keeps sending requests into the failure; a circuit breaker trips open and fails fast, giving the downstream time to recover. Use breakers on outbound calls, rate limiters on inbound traffic.

### Is uber-go/ratelimit still maintained?

It is stable and complete rather than actively developed — last push May 2024, with a deliberately tiny API that has not needed changes. The README explicitly recommends x/time/rate for complex use cases. For a hard per-second ceiling with minimal overhead it remains an excellent choice.

### How do I choose the burst size for x/time/rate?

Start from your handler's worst acceptable latency and typical concurrency. A good rule of thumb: burst should cover your expected concurrent requests so legitimate users never see 429s, while the rate controls sustained throughput. Watch `limiter.Tokens()` and your 429 rate in production and adjust.

### Should rate limiting live in the app or at the proxy?

Both, for different reasons. The proxy (nginx, Envoy, Kong) protects your infrastructure from floods before they reach your service; in-app limiters give you per-user/per-route granularity and business rules. Our [self-hosted rate limiting comparison](../2026-04-28-nginx-vs-caddy-vs-envoy-ratelimit-self-hosted-rate-limiting-guide-2026/) covers the proxy tier, and the [Java rate limiter libraries guide](../2026-06-19-rate-limiter-libraries-bucket4j-resilience4j-governor-guava/) shows the same decisions in another ecosystem.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
