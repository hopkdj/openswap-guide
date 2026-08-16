---
title: "Go HTTP Clients in 2026: resty vs fasthttp vs req — Which Should You Actually Use?"
date: "2026-08-17"
tags: ["golang", "http-client", "developer-tools", "rest-api"]
draft: false
cover: "/img/screenshots/resty-cover.jpg"
---

Your Go service needs to call an external REST API. The standard library's `net/http` will work — until you need per-request timeouts, automatic retries, backoff, auth headers, response auto-parsing, and debug logging. Then you hand-roll the same 250 lines of glue code for the fifth time, and you start wondering if anyone has already solved this. They have — three times over. **resty (11,751 stars), fasthttp (23,434 stars), and req (4,852 stars)** each take a different philosophy on how Go HTTP clients should work, and picking the wrong one costs you either performance or developer hours.

## TL;DR / Quick Verdict

If you build typical microservices, API integrations, or SDKs, choose **resty** — its fluent request builder and middleware system cover 95% of what you need out of the box. If you need maximum throughput on thousands of small requests per second with strict latency budgets, choose **fasthttp**, but only after benchmarking — its API is deliberately incompatible with `net/http`. If you want modern protocol support (HTTP/3), automatic retries, and zero-config request debugging with a smaller dependency footprint, choose **req**. For most teams, the honest answer is resty or req, and fasthttp only when your benchmarks prove you need it.

## Feature Comparison (live GitHub data, August 2026)

| Feature | resty v3 | fasthttp | req v3 |
|---|---|---|---|
| GitHub stars | 11,751 | 23,434 | 4,852 |
| Last push | 2026-07-26 | 2026-08-15 | 2026-08-13 |
| License | MIT | MIT | MIT |
| Minimum Go version | 1.23+ | 1.20+ | 1.24+ |
| API style | Fluent request builder (`client.R()`) | Low-level `RequestCtx` / custom `Client` | Fluent package-level + client API |
| HTTP/2 | Yes | Yes | Yes (auto-detect) |
| HTTP/3 | Yes (opt-in) | No | Yes (opt-in) |
| Automatic retry | Yes (customizable) | Manual | Yes (customizable) |
| Request/response middleware | Yes | Via `fasthttp.HostClient` hooks | Yes (4 layers) |
| Response auto-parse (JSON/XML) | Yes | No | Yes |
| Automatic charset decode | Yes | No | Yes |
| SSE client support | Yes | No | Partial |
| File upload/download with progress | Yes | Manual | Yes (progress callbacks) |
| `net/http` compatible interfaces | Yes | No | Yes (`req.Transport` swaps into `http.Client`) |

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Public REST API integration in a microservice | **resty** | Fluent builder, auto JSON parsing, retries, middleware — least code for the most common job |
| High-throughput proxy / gateway (10K+ req/s) | **fasthttp** | Zero allocations in hot paths; README benchmarks show 0 allocs/op vs 44–84 allocs/op for `net/http` |
| HTTP/3 or fingerprint-sensitive scraping | **req** | Native HTTP/3 support and HTTP fingerprint impersonation built in |
| SDK shipped to external Go consumers | **resty** | Familiar API, well-documented, stable v3, huge community |
| Replacing an existing `net/http` client incrementally | **req** | Exportable `req.Transport` drops into `http.Client` with minimal code change |
| Quick API smoke tests in a script | **req** | `req.DevMode()` + `req.MustGet()` gives full request/response dumps with zero setup |

## resty — The Batteries-Included Standard

resty v3 (vanity import `resty.dev/v3`) is the most popular high-level HTTP client for Go, and for good reason: it wraps `net/http` instead of replacing it, so every `*http.Response` and `http.Client` behavior you already know keeps working underneath. The core pattern is the request builder — create a client once, reuse it everywhere:

```go
// create a Resty client
client := resty.New()
defer client.Close()

res, err := client.R().
    SetQueryParams(map[string]string{
        "page_no": "1",
        "limit":   "20",
        "sort":    "name",
        "order":   "asc",
    }).
    SetHeader("Accept", "application/json").
    SetAuthToken("bc594900518b4f7eac75bd37f019e08f").
    Get("/search_result")

fmt.Println(err, res)
```

That snippet is from the official resty documentation, and it demonstrates the two things resty does best: **request-level configuration** (every `R()` call is an isolated request context) and **client-level configuration** (timeouts, retries, rate limiting, and tracing set once on `resty.New()`). Beyond the basics, resty v3 ships server-sent events (SSE) streaming, automatic load balancing across upstream hosts with service discovery, a built-in rate limiter, request tracing via the OpenTelemetry ecosystem, and curl-command generation for debugging (`client.R().SetCurlCommand(true)`).

**The catch:** resty's feature list is long, and that surface area shows in dependency weight and a learning curve for the middleware chain. Also note the v2 → v3 upgrade changed several APIs (most notably how clients are closed and how some middleware hooks are registered), so old v2 tutorials can mislead you.

## fasthttp — Raw Speed, Deliberate Trade-offs

fasthttp describes itself as "tuned for high performance. Zero memory allocations in hot paths." Its own README is refreshingly honest about the cost: *"fasthttp was designed for some high performance edge cases. Unless your server/client needs to handle thousands of small to medium requests per second and needs a consistent low millisecond response time, fasthttp might not be for you. For most cases `net/http` is much better."*

The client API is optimized for connection pooling and zero-copy reads. The official client example in the repo configures aggressive timeouts, a 10 MiB response cap, and a DNS cache:

```go
client = &fasthttp.Client{
    ReadTimeout:                   readTimeout,        // 500ms
    WriteTimeout:                  writeTimeout,       // 500ms
    MaxIdleConnDuration:           maxIdleConnDuration,// 1h
    MaxResponseBodySize:           10 * 1024 * 1024,   // Reject responses larger than 10 MiB
    NoDefaultUserAgentHeader:      true,
    DisableHeaderNamesNormalizing: true,
    DisablePathNormalizing:        true,
    // Increase DNS cache time to an hour instead of the default minute
    Dial: (&fasthttp.TCPDialer{
        Concurrency:      4096,
        DNSCacheDuration: time.Hour,
    }).Dial,
}
```

The README's client benchmarks (GOMAXPROCS=1, Xeon 2.2 GHz) show the payoff: `net/http`'s `ClientGetEndToEnd1TCP` runs at **55.6 µs/op with 70 allocations**, while fasthttp's equivalent runs at **26.5 µs/op with 0 allocations** — and the README claims up to 4× faster end to end. VertaMedia reportedly serves up to 200K requests/second from 1.5M concurrent keep-alive connections per physical server on fasthttp.

**The catch is structural:** fasthttp does not implement `http.Handler` or `http.Client` interfaces. You cannot pass a fasthttp client to code that expects `*http.Client`, and server handlers use `*fasthttp.RequestCtx` instead of `http.Request`. There is a conversion table in the README for migrating, but third-party libraries (OpenTelemetry instrumentation, most SDKs) generally assume `net/http` types. fasthttp also has no built-in HTTP/3.

## req — The Modern All-Rounder

req (pronounced "request") is the newest of the three and reads like a wish list of what resty does well plus modern protocol support. From its README: automatic retry with full customization, HTTP/1.1, HTTP/2, and HTTP/3 with automatic protocol detection, automatic UTF-8 decoding to avoid garbled characters, automatic request-body marshaling and response-body unmarshaling based on Content-Type, HTTP fingerprint impersonation for sites that block crawlers, and four layers of middleware (request, response, client, transport).

The zero-setup debugging story is unique. The README's quick-start literally dumps a full HTTP/2 request and response with one line:

```go
package main

import (
    "github.com/imroc/req/v3"
)

func main() {
    req.DevMode() // Treat the package name as a Client, enable development mode
    req.MustGet("https://httpbin.org/uuid") // Treat the package name as a Request, send GET request.

    req.EnableForceHTTP1() // Force using HTTP/1.1
    req.MustGet("https://httpbin.org/uuid")
}
```

Run that and you get colorized, timestamped dumps of every header and body for both HTTP/2 and HTTP/1.1 — the fastest way to debug an API integration without touching a proxy. For production, the README recommends explicitly creating a client and reusing it:

```go
client := req.C()
resp, err := client.R().
    SetHeader("Accept", "application/json").
    SetBody(map[string]interface{}{"name": "imroc"}).
    Post("https://httpbin.org/post")
```

req's exportable `Transport` is the killer migration feature: it implements `http.RoundTripper`, so you can swap it into an existing `net/http` client and immediately gain HTTP/3, response dumping, and middleware without rewriting your call sites.

## Common Pitfalls and Migration Gotchas

1. **Don't set a global timeout and forget request-scoped timeouts.** resty and req both support `SetTimeout` at client and request level. A client-wide 30s timeout will kill long file uploads; set per-request timeouts for those.
2. **fasthttp's incompatible interfaces are a one-way door.** Before adopting fasthttp, grep your codebase for `*http.Client` parameters — every SDK, instrumentation library, and test helper that accepts one will need a wrapper. The README's own advice is to stay on `net/http` unless benchmarks say otherwise.
3. **Connection reuse settings matter more than the client library.** DNS cache duration, max idle connections, and keep-alive settings dominate real-world latency. fasthttp's default DNS cache is 60 seconds — extend it (as the official example does) if you see DNS resolution in profiles.
4. **HTTP/3 requires explicit opt-in and UDP.** resty's `EnableHTTP3()` and req's `EnableHTTP3()` use the quic-go stack; behind corporate firewalls or NAT-heavy networks, UDP/443 may be blocked, so keep an HTTP/2 fallback path.
5. **Response body size limits.** fasthttp rejects responses larger than `MaxResponseBodySize` (set it explicitly, as in the official example). resty and req read unboundedly by default — streaming huge payloads through a client that buffers everything will spike memory.
6. **When migrating from resty v2 to v3**, the close-semantics of clients changed (`client.Close()` is now required to release pooled resources), and some middleware hooks moved. Read the official upgrade guide before bumping.

For routing and framework context on the server side of these clients, see our [Go HTTP routers comparison (chi vs gin vs echo vs fiber)](../2026-07-31-go-http-routers-chi-gin-echo-fiber/) and the [Go web frameworks guide](../2026-07-06-go-web-frameworks-gin-echo-fiber-chi/). If you work across languages, our [Java HTTP client libraries comparison](../2026-07-03-java-http-client-libraries-okhttp-retrofit-apache-httpclient-feign/) and [PHP HTTP clients guide](../2026-07-13-php-http-clients-guzzle-saloon-httpful/) show how the same trade-offs play out in other ecosystems.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go HTTP Clients in 2026: resty vs fasthttp vs req — Which Should You Actually Use?",
  "description": "Deep comparison of Go HTTP client libraries: resty v3, fasthttp, and req v3. Live GitHub stats, benchmarks, code examples, decision matrix, and migration pitfalls.",
  "datePublished": "2026-08-17",
  "dateModified": "2026-08-17",
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

**Is fasthttp worth it for a typical REST API consumer?**
Usually not. The README itself recommends `net/http` for most cases. fasthttp's zero-allocation hot paths pay off when you process thousands of small requests per second with tight latency budgets — benchmark your actual workload before switching.

**What is the difference between resty and req?**
resty is older, more established, and has the largest community; its middleware and SSE support are more mature. req is smaller and newer, with native HTTP/3, automatic charset decoding, and HTTP fingerprint impersonation. Both offer fluent APIs, retries, and JSON auto-parsing.

**Can I use these clients with code that expects `net/http`?**
resty and req yes — resty wraps `net/http`, and req exports a `Transport` that implements `http.RoundTripper`. fasthttp no: it uses its own `RequestCtx` and client types, so you cannot pass it to functions accepting `*http.Client`.

**Which Go version do I need?**
resty v3 requires Go 1.23+, req v3 requires Go 1.24+, and fasthttp supports older toolchains (1.20+). Check your module's `go` directive before upgrading.

**Do these libraries support HTTP/3?**
req supports HTTP/3 natively (opt-in), resty v3 supports it via `EnableHTTP3()`, and fasthttp does not. HTTP/3 needs UDP/443, so plan a fallback path for restricted networks.

**What should I do about retries for idempotent requests?**
resty and req both provide automatic retry with custom backoff. A common pattern is 3 retries with exponential backoff plus jitter, applied only to GET/HEAD/PUT/DELETE — never blindly retry POST unless your API guarantees idempotency keys.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
