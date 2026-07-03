---
title: "Self-Hosted Java HTTP Client Libraries: OkHttp vs Retrofit vs Apache HttpClient vs Feign"
date: "2026-07-03"
tags: ["java", "http", "http-client", "okhttp", "retrofit", "feign", "apache", "rest", "api", "comparison", "developer-tools"]
draft: false
---

Java's HTTP client ecosystem has evolved dramatically from the early days of `HttpURLConnection`. Modern applications need connection pooling, interceptors, type-safe request/response handling, and seamless integration with serialization libraries. This article compares four major Java HTTP client libraries — OkHttp, Retrofit, Apache HttpClient, and Feign — with code examples and guidance for different use cases.

## Comparison at a Glance

| Feature | OkHttp | Retrofit | Apache HttpClient | Feign |
|---------|--------|----------|-------------------|-------|
| **GitHub Stars** | 46,996 | 43,907 | 1,530 | 9,787 |
| **Abstraction Level** | Low-level HTTP | Declarative REST | Low-level HTTP | Declarative REST |
| **HTTP/2 Support** | Yes | Via OkHttp | Yes (v5+) | Via OkHttp/Apache |
| **Connection Pooling** | Yes | Via OkHttp | Yes | Via backend |
| **Interceptor Chain** | Yes | Yes | Yes | Yes |
| **Type-Safe API** | No | Yes (annotations) | No | Yes (annotations) |
| **Async Support** | Yes (Callbacks) | Yes (Call/Coroutines) | Yes (v5+) | Yes |
| **Last Updated** | Jul 2026 | Jun 2026 | Jul 2026 | Jul 2026 |

## Deep Dive: Each Library

### OkHttp — The Industry Standard HTTP Engine

OkHttp is Square's low-level HTTP client, known for efficiency, HTTP/2 support, and automatic connection recovery. It's the foundation Retrofit and many other libraries build upon.

```java
import okhttp3.*;

public class OkHttpExample {
    private final OkHttpClient client = new OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .addInterceptor(new LoggingInterceptor())
        .connectionPool(new ConnectionPool(5, 5, TimeUnit.MINUTES))
        .build();

    public String get(String url) throws IOException {
        Request request = new Request.Builder()
            .url(url)
            .header("Authorization", "Bearer " + token)
            .build();

        try (Response response = client.newCall(request).execute()) {
            return response.body().string();
        }
    }

    public String postJson(String url, String json) throws IOException {
        RequestBody body = RequestBody.create(
            json, MediaType.parse("application/json"));
        Request request = new Request.Builder()
            .url(url)
            .post(body)
            .build();

        try (Response response = client.newCall(request).execute()) {
            return response.body().string();
        }
    }
}
```

OkHttp's interceptor chain is its killer feature — add logging, authentication headers, retry logic, and caching transparently. Its connection pooling reuses TCP connections across requests, dramatically reducing latency in high-throughput services.

### Retrofit — Type-Safe REST Client

Retrofit, also from Square, turns REST APIs into Java interfaces using annotations. It delegates HTTP execution to OkHttp, giving you both type safety and OkHttp's performance.

```java
import retrofit2.*;
import retrofit2.http.*;

public interface GitHubService {
    @GET("users/{user}/repos")
    Call<List<Repo>> listRepos(@Path("user") String user);

    @POST("repos/{owner}/{repo}/issues")
    Call<Issue> createIssue(
        @Path("owner") String owner,
        @Path("repo") String repo,
        @Body Issue issue
    );
}

// Usage
Retrofit retrofit = new Retrofit.Builder()
    .baseUrl("https://api.github.com/")
    .addConverterFactory(GsonConverterFactory.create())
    .client(new OkHttpClient.Builder()
        .addInterceptor(new AuthInterceptor())
        .build())
    .build();

GitHubService service = retrofit.create(GitHubService.class);
List<Repo> repos = service.listRepos("octocat").execute().body();
```

Retrofit shines when you have well-defined REST APIs. Define the interface once, and Retrofit handles request building, response parsing, and error mapping. Converter factories let you plug in Gson, Jackson, Moshi, or Protobuf for serialization.

### Apache HttpClient — The Veteran

Apache HttpClient is the oldest and most battle-tested option, part of Apache's HttpComponents project. Version 5 modernized the API with HTTP/2, async support, and fluent builders.

```java
import org.apache.hc.client5.http.impl.classic.*;
import org.apache.hc.core5.http.io.entity.EntityUtils;
import org.apache.hc.core5.http.message.BasicClassicHttpRequest;
import org.apache.hc.core5.http.ClassicHttpResponse;

public class ApacheHttpExample {
    public String get(String url) throws Exception {
        try (CloseableHttpClient client = HttpClients.custom()
                .setConnectionManager(new PoolingHttpClientConnectionManager())
                .build()) {

            BasicClassicHttpRequest request = new BasicClassicHttpRequest("GET", url);
            request.addHeader("Authorization", "Bearer " + token);

            return client.execute(request, response -> {
                return EntityUtils.toString(response.getEntity());
            });
        }
    }
}
```

Apache HttpClient offers the most comprehensive configuration — custom SSL contexts, proxy routing, cookie management, and credential providers. It's the go-to choice for enterprise environments that need fine-grained control over HTTP behavior, especially when integrating with legacy systems that use non-standard TLS or authentication schemes.

### Feign — Declarative HTTP with Spring Integration

OpenFeign is a declarative HTTP client originally from Netflix, now part of Spring Cloud. Like Retrofit, you define interfaces with annotations — but Feign integrates deeply with Spring's ecosystem.

```java
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

@FeignClient(name = "user-service", url = "https://api.example.com")
public interface UserClient {
    @GetMapping("/users/{id}")
    User getUser(@PathVariable("id") Long id);

    @PostMapping("/users")
    User createUser(@RequestBody User user);
}

// Usage in a Spring service:
@Autowired
private UserClient userClient;

public User findUser(Long id) {
    return userClient.getUser(id);
}
```

Feign's killer feature is Spring Cloud integration — it automatically picks up service discovery (Eureka, Consul), client-side load balancing (Spring Cloud LoadBalancer), and circuit breakers (Resilience4j). In a microservices architecture, Feign reduces HTTP client code to almost nothing.

## Architecture Selection Guide

For **direct HTTP control** with maximum performance: use OkHttp. It's the fastest, most efficient low-level HTTP client in the JVM ecosystem and powers most higher-level libraries.

For **REST API consumption**: use Retrofit if you're outside Spring, or Feign if you're inside Spring. Both provide type-safe interfaces that eliminate manual JSON parsing and URL construction.

For **enterprise integration**: use Apache HttpClient when connecting to legacy services that require custom TLS, NTLM authentication, or non-standard HTTP dialects. Its configurability is unmatched.

For **microservices**: use Feign with Spring Cloud. The service discovery, load balancing, and circuit breaker integrations save hundreds of lines of infrastructure code.

## Why Self-Host Your HTTP Client Layer?

HTTP clients are the nervous system of distributed applications — every outbound API call passes through them. Choosing and self-hosting your HTTP client library rather than relying on platform-managed SDKs gives you control over connection pooling, timeouts, retry strategies, and observability. OkHttp's interceptor chain, for instance, lets you inject distributed tracing headers, rate-limit logic, and circuit breaker patterns without touching business code.

For Spring Boot applications building out their HTTP stack, our [Java web frameworks comparison](../2026-07-03-java-web-frameworks-spring-boot-quarkus-micronaut-helidon-javalin/) helps you choose the right server-side framework to pair with your HTTP client. If your API responses include complex JSON payloads, see our [Java JSON libraries guide](../2026-06-22-java-json-libraries-jackson-gson-moshi-guide/) for choosing the right serialization library to use with Retrofit or Feign converters.

For GraphQL-based backends, our [GraphQL server libraries comparison](../2026-06-20-graphql-server-libraries-apollo-yoga-mercurius-strawberry-hotchocolate/) covers alternatives that may replace REST HTTP clients entirely.
## Performance Benchmarks and Metrics

HTTP client performance directly impacts application responsiveness — every outbound API call adds latency your users experience. Understanding the performance characteristics of each library helps you make informed decisions.

### Connection Pooling Efficiency

OkHttp's connection pool reuses TCP connections aggressively, maintaining up to 5 idle connections per host by default. Each reused connection saves ~50-100ms of TCP/TLS handshake overhead. In a microservices environment making hundreds of requests per second, this translates to significant latency reduction.

Apache HttpClient v5's `PoolingHttpClientConnectionManager` offers more granular control — you can set per-route connection limits, validate connections before reuse, and configure eviction policies for stale connections:

```java
PoolingHttpClientConnectionManager cm = new PoolingHttpClientConnectionManager();
cm.setMaxTotal(200);
cm.setDefaultMaxPerRoute(20);
cm.setValidateAfterInactivity(5000); // Validate idle connections after 5s

CloseableHttpClient client = HttpClients.custom()
    .setConnectionManager(cm)
    .evictIdleConnections(30, TimeUnit.SECONDS)
    .build();
```

### Throughput Considerations

For high-throughput services (10,000+ requests/second), OkHttp is the clear winner. Its non-blocking I/O architecture and minimal allocation overhead make it the fastest JVM HTTP client in most benchmarks. Retrofit adds negligible overhead since it delegates entirely to OkHttp.

Feign's performance depends on the underlying client — by default it uses `HttpURLConnection`, but configuring it to use OkHttp brings performance parity. Apache HttpClient v5 with async I/O performs well at moderate throughput but shows higher memory pressure than OkHttp under extreme load due to its more complex request/response object model.

### Observability and Metrics

All four libraries support metrics collection through interceptors or event listeners. For OkHttp, implement an `EventListener` to track DNS resolution time, connection establishment, TLS handshake, and request/response body transfer individually. Export these metrics to Prometheus for dashboarding and alerting on p95/p99 latency regressions.

## FAQ

### Should I use the built-in `java.net.http.HttpClient` (Java 11+) instead of these libraries?

Java 11's built-in `HttpClient` is a solid choice for simple applications — it supports HTTP/2, async requests, and WebSocket. However, it lacks OkHttp's interceptor chain, connection pool tuning, and Retrofit/Feign's declarative API support. For production microservices, OkHttp or Retrofit provide better ergonomics and ecosystem integration.

### Can I use Retrofit without OkHttp?

Yes. Retrofit 2.x allows custom `Call.Factory` implementations. You can configure Retrofit to use Java 11's `HttpClient`, Apache HttpClient, or any HTTP engine. However, OkHttp is the default and most tested backend.

### How do Feign and Retrofit compare for non-Spring projects?

For non-Spring projects, Retrofit is the better choice. Feign's primary advantage is Spring Cloud integration — outside that ecosystem, Retrofit's API is more mature, better documented, and has a larger community. Retrofit has been around longer (since 2012) and has extensive documentation for standalone use.

### What's the best approach for handling retry logic?

OkHttp's interceptor chain is ideal for retry logic. Add a `RetryInterceptor` that catches `IOException` and retries with exponential backoff. For Feign, Spring Retry or Resilience4j provides declarative retry annotations. Retrofit can use OkHttp interceptors or RxJava's `retryWhen()` operator.

### How do these libraries compare in terms of memory and performance overhead?

OkHttp has the lowest overhead — it's designed for mobile (Android) where memory is constrained. Apache HttpClient v5 is heavier but offers more features. Retrofit adds minimal overhead on top of OkHttp (mostly reflection at startup). Feign's overhead depends on Spring context — it's heavier to initialize but comparable at runtime.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Self-Hosted Java HTTP Client Libraries: OkHttp vs Retrofit vs Apache HttpClient vs Feign",
  "description": "Compare four Java HTTP client libraries — OkHttp, Retrofit, Apache HttpClient, and Feign — with code examples, architecture guidance, and Spring integration patterns.",
  "datePublished": "2026-07-03",
  "dateModified": "2026-07-03",
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
