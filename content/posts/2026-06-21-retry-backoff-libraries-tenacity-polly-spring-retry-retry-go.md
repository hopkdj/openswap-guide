---
title: "Self-Hosted Retry & Backoff Libraries: Tenacity vs Polly vs Spring Retry vs retry-go — Resilient Operations Guide"
date: "2026-06-21"
tags: ["retry", "backoff", "resilience", "python", "golang", "java", "dotnet", "developer-libraries", "fault-tolerance"]
draft: false
---

## Introduction

In distributed systems, transient failures are inevitable. Network timeouts, database deadlocks, temporary service unavailability, and rate limit responses all require applications to handle failure gracefully. **Retry libraries** provide structured, configurable mechanisms for retrying failed operations with exponential backoff, jitter, and circuit-breaking patterns.

Manually implementing retry logic with `for` loops and `sleep()` calls leads to brittle, error-prone code. Dedicated retry libraries handle edge cases like max retry counts, backoff strategies, retry predicates, and integration with monitoring systems. In this article, we compare four leading open-source retry libraries across different language ecosystems: **Tenacity** (Python, 8,674 ⭐), **Polly** (.NET, 14,189 ⭐), **Spring Retry** (Java, 2,268 ⭐), and **retry-go** (Go, 2,929 ⭐).

## Comparison Table

| Feature | Tenacity (Python) | Polly (.NET) | Spring Retry (Java) | retry-go (Go) |
|---------|-------------------|--------------|---------------------|---------------|
| Stars | 8,674 | 14,189 | 2,268 | 2,929 |
| Language | Python | C# / .NET | Java | Go |
| Backoff Strategies | fixed, exponential, random, fibonacci | fixed, exponential, linear | fixed, exponential, random | fixed, exponential |
| Jitter Support | Yes (full, equal) | Yes (via DecorrelatedJitter) | Via custom BackOffPolicy | Via custom delay func |
| Retry Predicates | Exception types, result checks | Exception types, result, custom | Exception types, result | Error types, response check |
| Async Support | Native (asyncio) | Native (async/await) | @Async annotation | Native goroutines |
| Callbacks | before_sleep, after_attempt | onRetry, onFallback | RecoveryCallback | OnRetry func |
| Statistics | Built-in (attempt_number) | Via PolicyRegistry | RetryContext | Manual tracking |
| Last Updated | Jun 2026 | Jun 2026 | Jun 2026 | Feb 2026 |

## Tenacity — Python's Retry Powerhouse

[Tenacity](https://github.com/jd/tenacity) is the gold standard for retry logic in Python, used by projects ranging from data pipelines to API clients and distributed task queues. It's a fork of the older `retrying` library with significant improvements in usability and features.

**Key Features:**
- **Decorator-based API**: Minimal code changes to add retry behavior
- **Wait strategies**: `wait_fixed`, `wait_exponential`, `wait_random`, `wait_chain`
- **Stop conditions**: `stop_after_attempt`, `stop_after_delay`, `stop_never`, `stop_all`
- **Retry predicates**: `retry_if_exception_type`, `retry_if_result`, custom callables
- **Before/after hooks**: `before_sleep`, `after_attempt`, `before_log`

**Basic Usage:**

```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import logging
import requests
from requests.exceptions import ConnectionError, Timeout

logger = logging.getLogger(__name__)

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((ConnectionError, Timeout)),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
def fetch_api_data(url: str) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

# Result-based retry
@retry(
    stop=stop_after_attempt(3),
    retry=lambda resp: resp.status_code >= 500
)
def call_external_service(payload: dict):
    return requests.post("https://api.example.com/process", json=payload)
```

**Async Usage with asyncio:**

```python
from tenacity import retry, stop_after_attempt, wait_exponential
import httpx

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30)
)
async def fetch_async(client: httpx.AsyncClient, url: str):
    response = await client.get(url)
    response.raise_for_status()
    return response.json()
```

Tenacity's combination of decorator simplicity and fine-grained configuration makes it the most productive choice for Python developers. The `wait_chain` feature is particularly powerful for implementing multi-phase backoff strategies (e.g., retry every 2 seconds for the first 3 attempts, then switch to exponential backoff).

## Polly — .NET's Resilience Swiss Army Knife

[Polly](https://github.com/App-vNext/Polly) is much more than a retry library — it's a comprehensive resilience and transient-fault-handling library for .NET. In addition to retry, it provides circuit breaker, timeout, bulkhead isolation, fallback, and hedging policies.

**Key Features:**
- **Policy composition**: Combine retry with circuit breaker, timeout, and fallback
- **Policy registry**: Centralized management of named policies with metrics
- **Fluent API**: Intuitive builder pattern for policy construction
- **HttpClient integration**: Native `IHttpClientFactory` extensions
- **Distributed caching**: Polly caching policy with pluggable cache providers

**Basic Usage:**

```csharp
using Polly;
using Polly.Retry;

// Simple retry with exponential backoff
var retryPolicy = Policy
    .Handle<HttpRequestException>()
    .Or<TimeoutException>()
    .OrResult<HttpResponseMessage>(r => (int)r.StatusCode >= 500)
    .WaitAndRetryAsync(
        retryCount: 5,
        sleepDurationProvider: attempt =>
            TimeSpan.FromSeconds(Math.Pow(2, attempt)) + TimeSpan.FromMilliseconds(new Random().Next(0, 1000)),
        onRetry: (outcome, timespan, attempt, context) =>
        {
            Console.WriteLine($"Retry {attempt} after {timespan.TotalSeconds:F1}s");
        });

// Execute with policy
var response = await retryPolicy.ExecuteAsync(async () =>
{
    var client = new HttpClient();
    return await client.GetAsync("https://api.example.com/data");
});
```

**Combining Policies (Retry + Circuit Breaker):**

```csharp
var circuitBreaker = Policy
    .Handle<HttpRequestException>()
    .CircuitBreakerAsync(
        exceptionsAllowedBeforeBreaking: 3,
        durationOfBreak: TimeSpan.FromSeconds(30)
    );

var retry = Policy
    .Handle<HttpRequestException>()
    .WaitAndRetryAsync(3, attempt =>
        TimeSpan.FromSeconds(Math.Pow(2, attempt))
    );

// Compose: retry first, then open circuit breaker
var combined = Policy.WrapAsync(circuitBreaker, retry);

await combined.ExecuteAsync(async () =>
    await httpClient.GetAsync("https://api.example.com/data"));
```

Polly's policy composition architecture is its killer feature: you can layer retry, circuit breaker, timeout, and fallback policies into a single coherent resilience strategy. This makes Polly the best choice for .NET applications that need comprehensive fault tolerance beyond simple retries.

## Spring Retry — Java's Declarative Approach

[Spring Retry](https://github.com/spring-projects/spring-retry) integrates retry capabilities directly into the Spring Framework ecosystem. It supports both annotation-based declarative retry and programmatic `RetryTemplate` usage.

**Key Features:**
- **@Retryable annotation**: Declarative retry on Spring-managed beans
- **@Recover fallback**: Automatic fallback method invocation after exhaustion
- **BackOffPolicy implementations**: ExponentialBackOffPolicy, FixedBackOffPolicy, UniformRandomBackOffPolicy
- **RetryTemplate**: Programmatic retry with callback-based API
- **Spring Boot auto-configuration**: Zero-config setup in Spring Boot applications

**Basic Usage — Declarative:**

```java
@Service
public class PaymentService {
    
    @Retryable(
        retryFor = { HttpClientErrorException.TooManyRequests.class, 
                     ResourceAccessException.class },
        maxAttempts = 4,
        backoff = @Backoff(delay = 1000, multiplier = 2.0, maxDelay = 30000)
    )
    public PaymentResponse processPayment(PaymentRequest request) {
        return restTemplate.postForObject(
            "https://payment-gateway.example.com/charge",
            request,
            PaymentResponse.class
        );
    }
    
    @Recover
    public PaymentResponse fallbackPayment(
            HttpClientErrorException e, PaymentRequest request) {
        // Queue for async retry or notify admin
        paymentQueue.add(request);
        return PaymentResponse.queued();
    }
}
```

**Programmatic Usage with RetryTemplate:**

```java
@Configuration
public class RetryConfig {
    
    @Bean
    public RetryTemplate retryTemplate() {
        RetryTemplate template = new RetryTemplate();
        
        // Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 5 attempts)
        ExponentialBackOffPolicy backOffPolicy = new ExponentialBackOffPolicy();
        backOffPolicy.setInitialInterval(1000);
        backOffPolicy.setMultiplier(2.0);
        backOffPolicy.setMaxInterval(30000);
        
        // Stop after 5 attempts
        SimpleRetryPolicy retryPolicy = new SimpleRetryPolicy();
        retryPolicy.setMaxAttempts(5);
        
        template.setBackOffPolicy(backOffPolicy);
        template.setRetryPolicy(retryPolicy);
        return template;
    }
    
    public <T> T executeWithRetry(RetryCallback<T, Exception> callback) {
        return retryTemplate().execute(callback);
    }
}
```

Spring Retry's tight integration with the Spring ecosystem is its main advantage: `@Retryable` works seamlessly with `@Transactional`, `@Async`, and Spring's AOP proxy system. The `@Recover` annotation provides a clean fallback pattern that keeps error handling separate from business logic.

## retry-go — Go's Minimalist Solution

[retry-go](https://github.com/avast/retry-go) delivers retry capabilities with Go's characteristic minimalism. It's a single-file library with zero external dependencies, focused on doing one thing well.

**Key Features:**
- **Functional options pattern**: Clean, extensible configuration via variadic options
- **Context support**: Native `context.Context` integration for cancellation and deadlines
- **Delay type flexibility**: `FixedDelay`, `BackOffDelay`, `CombineDelay`
- **Max jitter**: Built-in jitter to prevent thundering herd
- **onRetry callback**: Logging and metrics integration

**Basic Usage:**

```go
package main

import (
    "context"
    "fmt"
    "time"
    "github.com/avast/retry-go/v4"
)

func fetchRemoteConfig(ctx context.Context) ([]byte, error) {
    var config []byte
    
    err := retry.Do(
        func() error {
            var err error
            config, err = makeAPIRequest(ctx)
            return err
        },
        retry.Attempts(5),
        retry.Delay(2 * time.Second),
        retry.MaxDelay(30 * time.Second),
        retry.DelayType(retry.BackOffDelay),
        retry.MaxJitter(500 * time.Millisecond),
        retry.OnRetry(func(n uint, err error) {
            log.Printf("Retry #%d after error: %v", n, err)
        }),
        retry.Context(ctx),
        retry.RetryIf(func(err error) bool {
            // Only retry on specific errors
            var retryable *RetryableError
            return errors.As(err, &retryable) || isNetworkError(err)
        }),
    )
    
    return config, err
}
```

**Retry with Result Caching:**

```go
// retry-go supports returning values from retried functions
func getWithRetry(ctx context.Context, url string) (string, error) {
    var result string
    
    err := retry.Do(
        func() error {
            resp, err := http.Get(url)
            if err != nil {
                return err
            }
            defer resp.Body.Close()
            
            if resp.StatusCode >= 500 {
                return fmt.Errorf("server error: %d", resp.StatusCode)
            }
            
            body, _ := io.ReadAll(resp.Body)
            result = string(body)
            return nil
        },
        retry.Attempts(3),
        retry.DelayType(retry.BackOffDelay),
    )
    
    return result, err
}
```

retry-go's functional options pattern is idiomatic Go and integrates naturally with Go's error handling conventions. The library is small enough (~300 lines) to vendor directly into your project, making it ideal for teams that prefer dependency minimization.

## Choosing the Right Retry Library

- **Choose Tenacity if**: You're building Python services, data pipelines, or async applications. Tenacity's decorator API is the most ergonomic and its async support is first-class.
- **Choose Polly if**: You're on .NET and need a complete resilience strategy (not just retry). Polly's policy composition enables retry + circuit breaker + fallback in one coherent pipeline.
- **Choose Spring Retry if**: You're in the Spring/Java ecosystem and want declarative, annotation-driven retry with automatic `@Recover` fallback methods. The Spring Boot auto-configuration makes setup trivial.
- **Choose retry-go if**: You want a lightweight, dependency-free Go library that follows Go idioms. Its functional options pattern and context support make it feel native to the language.

For related resilience patterns, see our guides on [circuit breaker libraries](../2026-06-21-circuit-breaker-libraries-resilience4j-hystrix-failsafe-go-polly/) for preventing cascading failures, and [rate limiter implementations](../2026-06-19-rate-limiter-libraries-bucket4j-resilience4j-governor-guava/) for upstream protection. For broker-based resilience, our [message broker HA guide](../2026-06-01-self-hosted-message-broker-ha-rabbitmq-kafka-nats-guide/) covers retry-aware messaging patterns.

## FAQ

### What's the difference between retry and circuit breaker?

Retry re-attempts a failed operation immediately or after a short delay, assuming the failure is transient (network blip, brief overload). Circuit breaker stops calling a failing service entirely after a threshold of failures, preventing cascading failures and giving the downstream service time to recover. They're complementary — use retry for transient errors and circuit breaker for systemic failures.

### How do I prevent retry storms (thundering herd)?

Use **jitter** — random variation in the delay between retries. All four libraries support jitter. Without it, multiple clients hitting the same backoff schedule will synchronize their retries, overloading the recovering service. With jitter, retries are spread across time, giving the service breathing room.

### Should I retry on all errors or only specific ones?

Retry only on **transient** errors (network timeouts, 429 Too Many Requests, 503 Service Unavailable, temporary deadlocks). Never retry on **permanent** errors (400 Bad Request, 401 Unauthorized, validation failures) — retrying won't fix them and wastes resources. All four libraries support error type filtering to enforce this distinction.

### How many retry attempts should I configure?

Start with 3 attempts (1 initial + 2 retries) for user-facing operations and 5 for background tasks. More than 5 retries usually indicates a systemic problem that retry can't solve — circuit breaker or alerting should kick in. Configure `maxDelay` to cap the total retry duration (e.g., 30-60 seconds).

### Can I persist retry state across application restarts?

Tenacity and Polly don't persist retry state natively — they're in-memory. For durable retry across restarts, use a message queue (RabbitMQ, NATS) or task queue (Celery, BullMQ) with built-in retry mechanisms. Spring Retry can be combined with Spring Batch for checkpointed retry in long-running jobs.

### How do I monitor retry behavior in production?

All four libraries provide hooks for logging and metrics. In production, track: retry attempt count per operation (spiking counts indicate growing instability), success-after-retry rate (healthy if >90%), and max-attempts-exhausted events (actionable failures). Export to Prometheus/Grafana or your APM tool for dashboards and alerting.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Retry & Backoff Libraries: Tenacity vs Polly vs Spring Retry vs retry-go — Resilient Operations Guide",
  "description": "Compare four open-source retry and backoff libraries across Python (Tenacity), .NET (Polly), Java (Spring Retry), and Go (retry-go). Covers exponential backoff, jitter, retry predicates, async support, and integration patterns for building resilient distributed systems.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
