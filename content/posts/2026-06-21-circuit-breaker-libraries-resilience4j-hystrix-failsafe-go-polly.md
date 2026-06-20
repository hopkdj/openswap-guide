---
title: "Self-Hosted Circuit Breaker Libraries: Resilience4j vs Hystrix vs failsafe-go vs Polly"
date: "2026-06-21"
tags: ["circuit-breaker", "microservices", "resilience", "fault-tolerance", "java", "go", "dotnet", "developer-libraries", "comparison"]
draft: false
---

When building distributed systems and microservices architectures, one of the most critical patterns is the **circuit breaker**. Originally described by Michael Nygard in "Release It!", circuit breakers prevent cascading failures by detecting when a downstream service is failing and temporarily blocking requests to it — giving the system time to recover instead of piling on more load.

While infrastructure-level circuit breakers like [Envoy and HAProxy](../2026-05-01-self-hosted-circuit-breaker-envoy-haproxy-linkerd-fault-tolerance-guide/) operate at the network proxy layer, **library-level circuit breakers** live inside your application code. They offer finer-grained control, custom fallback logic, and deep integration with your service's business logic. In this article, we compare four leading open-source circuit breaker libraries across Java, Go, and .NET ecosystems.

## Why Use Library-Level Circuit Breakers?

Infrastructure circuit breakers work at the connection level — they can detect TCP failures and HTTP 5xx errors, but they cannot understand application-level semantics. A library-level circuit breaker can:

- **Distinguish between transient and permanent failures** — a timeout may be temporary, but an "insufficient funds" error is definitive
- **Execute custom fallback logic** — return cached data, call a backup service, or degrade gracefully
- **Track business metrics** — circuit state changes can trigger alerts, increment counters, or feed dashboards
- **Apply per-endpoint policies** — different endpoints may have different timeout and threshold configurations

For a broader look at resilience patterns in distributed systems, see our [distributed transactions guide](../2026-05-18-self-hosted-distributed-transactions-seata-cap-hmily-guide/) and our [rate limiter libraries comparison](../2026-06-19-rate-limiter-libraries-bucket4j-resilience4j-governor-guava/).

## Comparison Table

| Feature | Resilience4j | Netflix Hystrix | failsafe-go | Polly |
|---------|-------------|-----------------|-------------|-------|
| **Language** | Java | Java | Go | .NET (C#) |
| **GitHub Stars** | 10,692 | 24,460 | 2,226 | 14,189 |
| **Last Updated** | June 2026 | Dec 2025 | June 2026 | June 2026 |
| **Maintenance Status** | Active | Maintenance mode | Active | Active |
| **Circuit Breaker** | ✅ Sliding window | ✅ Rolling window | ✅ Count-based | ✅ Advanced policy |
| **Retry** | ✅ | ✅ (via Hystrix) | ✅ | ✅ |
| **Bulkhead** | ✅ Semaphore + ThreadPool | ✅ | ❌ | ✅ |
| **Rate Limiter** | ✅ | ❌ | ✅ | ✅ |
| **Time Limiter** | ✅ | ❌ | ✅ | ✅ |
| **Cache** | ✅ | ✅ | ❌ | ✅ |
| **Functional Programming** | ✅ Vavr/JDK functions | ❌ | ✅ Go idioms | ✅ LINQ |
| **Metrics Integration** | Micrometer, Dropwizard | Hystrix Dashboard | Prometheus, expvar | .NET metrics |
| **Modular Design** | ✅ Composable modules | Monolithic | ✅ Composable | ✅ Policies pipeline |

## Resilience4j: The Modern Java Standard

Resilience4j is the spiritual successor to Hystrix, designed for Java 8+ and functional programming. It's **modular** — you only import what you need — and integrates seamlessly with Spring Boot, Micrometer, and reactive stacks.

```java
// Resilience4j Circuit Breaker with Spring Boot
@Bean
public CircuitBreakerConfig circuitBreakerConfig() {
    return CircuitBreakerConfig.custom()
        .failureRateThreshold(50)
        .slowCallRateThreshold(50)
        .slowCallDurationThreshold(Duration.ofSeconds(2))
        .waitDurationInOpenState(Duration.ofSeconds(30))
        .permittedNumberOfCallsInHalfOpenState(3)
        .slidingWindowType(SlidingWindowType.COUNT_BASED)
        .slidingWindowSize(10)
        .build();
}

@CircuitBreaker(name = "paymentService", fallbackMethod = "fallback")
public PaymentResponse processPayment(PaymentRequest request) {
    return paymentClient.process(request);
}

public PaymentResponse fallback(PaymentRequest request, Exception ex) {
    log.warn("Circuit open for payment service, using cached response");
    return cache.get(request.getId());
}
```

**Key strengths**: Modular architecture (only import circuit-breaker, retry, bulkhead, etc. as needed), excellent Spring Boot auto-configuration, reactive support for WebFlux, and active community with regular releases.

## Netflix Hystrix: The Pioneer (Maintenance Mode)

Hystrix was the first widely-adopted circuit breaker library, battle-tested at Netflix scale. It's now in **maintenance mode** — Netflix recommends Resilience4j for new projects — but it still powers thousands of production systems and remains invaluable for maintaining legacy services.

```java
// Hystrix Command with fallback
public class GetUserCommand extends HystrixCommand<User> {
    private final String userId;
    
    public GetUserCommand(String userId) {
        super(HystrixCommandGroupKey.Factory.asKey("UserService"));
        this.userId = userId;
    }
    
    @Override
    protected User run() {
        return userService.getUser(userId);
    }
    
    @Override
    protected User getFallback() {
        return User.ANONYMOUS; // graceful degradation
    }
}
```

**Legacy strengths**: Mature and well-documented, Hystrix Dashboard for real-time monitoring, thread pool isolation by default, and proven at extreme scale. The main drawback is the lack of active development — no new features, and bug fixes are community-driven.

## failsafe-go: Resilience Patterns for Go

failsafe-go brings circuit breaker, retry, rate limiter, and timeout patterns to Go applications. It's designed with Go idioms in mind — no annotations or reflection, just clean function composition.

```go
// failsafe-go Circuit Breaker with Retry
circuitBreaker := circuitbreaker.Builder[any]().
    WithFailureRateThreshold(50, 10).
    WithDelay(30 * time.Second).
    Build()

retryPolicy := retry.Builder[any]().
    WithMaxRetries(3).
    WithBackoff(100*time.Millisecond, 2*time.Second).
    Build()

result, err := failsafe.Get(func() (string, error) {
    return callExternalService()
}, circuitBreaker, retryPolicy)
```

**Key strengths**: Clean, composable Go API; supports circuit breaker, retry, rate limiter, timeout, bulkhead, and cache; active development with regular releases; and first-class context support for cancellation and deadlines.

## Polly: .NET Resilience Powerhouse

Polly is the standard for resilience in the .NET ecosystem. It expresses resilience policies as a **pipeline** that can be composed and reused across your application.

```csharp
// Polly Circuit Breaker with Retry pipeline
var circuitBreaker = Policy
    .Handle<HttpRequestException>()
    .CircuitBreakerAsync(
        exceptionsAllowedBeforeBreaking: 3,
        durationOfBreak: TimeSpan.FromSeconds(30),
        onBreak: (ex, ts) => Log.Warning("Circuit broken!"),
        onReset: () => Log.Information("Circuit reset"));

var retry = Policy
    .Handle<HttpRequestException>()
    .WaitAndRetryAsync(3, retryAttempt =>
        TimeSpan.FromSeconds(Math.Pow(2, retryAttempt)));

var policyWrap = Policy.WrapAsync(retry, circuitBreaker);

var response = await policyWrap.ExecuteAsync(
    () => httpClient.GetAsync("/api/orders"));
```

**Key strengths**: Comprehensive resilience patterns (retry, circuit breaker, timeout, bulkhead, cache, fallback, rate limiter), fluent policy composition, deep .NET ecosystem integration, and excellent documentation.

## Why Self-Host Your Circuit Breaker Logic?

While cloud platforms offer managed resilience features, library-level circuit breakers provide several advantages for self-hosted deployments:

**Complete control over failure semantics** — You define what constitutes a failure. A 404 might be expected, while a 503 means the service is unhealthy. This granularity is impossible with proxy-layer circuit breakers alone.

**Zero external dependencies** — No need for a service mesh, sidecar proxy, or external coordination service. Your circuit breaker state lives in-process, which means no network hops for state checks.

**Custom fallback behavior** — Library circuit breakers can execute arbitrary fallback logic: return cached data, query a read replica, or degrade to a simpler computation path. This is far more flexible than returning a static error page.

**Cost efficiency** — At scale, avoiding the overhead of an additional proxy layer (Envoy, Linkerd) reduces infrastructure costs and operational complexity. Your application already has the resilience built in.

For more on building resilient microservices, see our [guide to microservices frameworks](../2026-05-03-dapr-vs-go-micro-vs-go-kit-self-hosted-microservices-frameworks-guide/) and our [distributed locking comparison](../self-hosted-distributed-locking-etcd-zookeeper-consul-redis-guide-2026/).

## Choosing the Right Library

- **New Java projects**: Choose Resilience4j — modular, actively maintained, and Spring-native
- **Legacy Java/Hystrix systems**: Continue with Hystrix until migration is prioritized, then move to Resilience4j
- **Go microservices**: failsafe-go is the clear leader with its composable, idiomatic API
- **.NET applications**: Polly is the ecosystem standard with comprehensive resilience patterns
- **Polyglot architectures**: Each service can use its language-appropriate library; consistency comes from configuration (thresholds, timeouts) rather than implementation

## FAQ

### What is the difference between a circuit breaker and a retry pattern?

A retry pattern simply repeats a failed operation, hoping it succeeds on a subsequent attempt. A circuit breaker monitors failure rates and **stops calling** the failing service entirely for a cooldown period — preventing retry storms from overwhelming an already-struggling downstream service. They work best together: retry handles transient failures, while the circuit breaker steps in when failures are persistent.

### Can I use multiple circuit breaker libraries in the same application?

Technically yes, but it creates confusion. If you have a Java service using Resilience4j and a Go service using failsafe-go, that's perfectly fine — each service uses the right tool for its language. Within a single process, stick to one library to avoid conflicting circuit states and inconsistent configuration.

### How do circuit breaker libraries handle state persistence?

Most library-level circuit breakers keep state **in memory only** — when your application restarts, the circuit resets to closed. This is generally desirable because a restart implies the environment has changed. If you need persistent circuit state across restarts, consider infrastructure-level solutions like [Envoy's outlier detection](../2026-05-01-self-hosted-circuit-breaker-envoy-haproxy-linkerd-fault-tolerance-guide/) or a service mesh.

### What metrics should I monitor for circuit breakers?

Track **circuit state transitions** (closed → open → half-open), **failure rate** vs threshold, **successful calls in half-open state**, and **fallback invocation count**. Resilience4j exports these via Micrometer; Hystrix has its dashboard; failsafe-go provides Prometheus metrics; Polly integrates with .NET metrics and Application Insights.

### When should I avoid library-level circuit breakers?

If you don't control the application code (e.g., third-party services, legacy monoliths), use infrastructure-level circuit breakers instead. If your team lacks the discipline to configure timeouts and thresholds per-endpoint, a service mesh with defaults may be safer. If you need circuit state coordinated across multiple instances of the same service, consider a distributed circuit breaker (though this adds significant complexity).

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Circuit Breaker Libraries: Resilience4j vs Hystrix vs failsafe-go vs Polly",
  "description": "Comprehensive comparison of open-source circuit breaker libraries for Java, Go, and .NET microservices — Resilience4j, Netflix Hystrix, failsafe-go, and Polly — with code examples, configuration guides, and resilience pattern recommendations.",
  "datePublished": "2026-06-21",
  "dateModified": "2026-06-21",
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
