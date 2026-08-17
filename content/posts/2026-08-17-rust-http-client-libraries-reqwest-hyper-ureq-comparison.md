---
title: "Rust HTTP Clients in 2026: reqwest vs hyper vs ureq — Which Should You Use?"
date: "2026-08-17"
tags: ["rust", "http", "http-client", "reqwest", "hyper", "ureq", "developer-tools", "backend"]
draft: false
cover: "/img/screenshots/reqwest-cover.jpg"
---

Rust has more than 50 published HTTP client crates, but almost every real project comes down to the same three names: **reqwest (11,782 stars)**, **hyper (16,276 stars)**, and **ureq (2,171 stars)**. Pick wrong and you are not just choosing an API — you are choosing an entire concurrency model, a TLS stack, and a dependency tree that can double your compile time. Pick right and you get a client that stays out of your way for years.

The trap is that these three crates look interchangeable at first glance — they all send GET requests — yet they solve fundamentally different problems. reqwest is a batteries-included client, hyper is a protocol foundation that web frameworks are built on, and ureq is a blocking client with zero unsafe code and nearly zero dependencies. This guide breaks down exactly which one you should reach for, with real code from the official repositories and live GitHub data as of August 2026.

## TL;DR: Quick Verdict

**Choose reqwest** if you want a full-featured client with JSON, cookies, redirects, proxies, and both async and blocking APIs — it is the right default for 80% of applications. **Choose hyper** only if you are building an HTTP server, a proxy, or a library that needs to control the protocol itself — it is a foundation, not a convenience layer. **Choose ureq** for small CLI tools, scripts, and embedded contexts where compile time, binary size, and a simple blocking model matter more than raw throughput. If you need the fastest possible async client, pair hyper's connection layer with a high-level wrapper rather than hand-rolling one.

## Quick Comparison: Feature by Feature

| Feature | reqwest 0.13 | hyper 1.x | ureq 3.x |
|---|---|---|---|
| GitHub stars (2026-08) | 11,782 | 16,276 | 2,171 |
| Last push (2026-08) | 2026-08-10 | 2026-08-15 | 2026-08-08 |
| Concurrency model | async + blocking | async only | blocking only |
| HTTP/1.1 + HTTP/2 | Yes | Yes | HTTP/1.1 (+ h2 via upgrade) |
| JSON built-in | Yes (`json` feature) | No | Yes (`json` feature) |
| Cookie store | Yes | No | Yes (`cookies` feature) |
| Automatic redirects | Configurable policy | No | Follows redirects |
| TLS backend | rustls / native-tls | Any (you supply) | rustls / native-tls |
| `unsafe` code | Yes (internally) | Yes (internally) | Forbidden |
| Compile-time footprint | Large (tokio + friends) | Medium | Minimal |
| Best for | Applications | Frameworks, servers, proxies | CLIs, scripts, embedded |

The table above is the whole story in one glance: each crate occupies a different rung of the abstraction ladder. reqwest is built *on top of* hyper, and both are async — ureq deliberately rejects async to stay small and simple.

## Use-Case Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| REST API client in a web service | **reqwest** | Async, JSON, retries, cookies, and TLS all handled for you |
| CLI tool that fetches one endpoint | **ureq** | 1-2 dependencies, sub-second compile, blocking reads are natural in CLIs |
| Building a web framework or router | **hyper** | axum, warp, and reqwest itself are built on it — it is the stable foundation |
| Reverse proxy / gateway in Rust | **hyper** | Connection-level control, HTTP/2, and full duplex streaming |
| Embedded / WASM client | **reqwest** | Official WASM support; ureq has no WASM story |
| Rapid prototype where compile time hurts | **ureq** | Full compile in seconds vs. minutes for a tokio tree |
| Microservice with heavy fan-out | **reqwest** | Connection pooling and HTTP/2 multiplexing out of the box |

## reqwest: The Batteries-Included Workhorse

reqwest describes itself as "an ergonomic, batteries-included HTTP Client," and that is exactly what it is. One crate gives you async and blocking clients, JSON serialization, multipart uploads, customizable redirect policies, HTTP proxies, a cookie store, and TLS via rustls or native-tls. It is the crate that most Rust developers mean when they say "the HTTP client."

The canonical example from the official repository shows how little ceremony is involved:

```toml
[dependencies]
reqwest = { version = "0.13", features = ["json"] }
tokio = { version = "1", features = ["full"] }
```

```rust
use std::collections::HashMap;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let resp = reqwest::get("https://httpbin.org/ip")
        .await?
        .json::<HashMap<String, String>>()
        .await?;
    println!("{resp:#?}");
    Ok(())
}
```

That is the entire client — URL, await, parse JSON. For production you will usually create a `Client` once and reuse it, because reqwest pools connections and reuses them across requests, which matters enormously under load:

```rust
let client = reqwest::Client::builder()
    .timeout(std::time::Duration::from_secs(10))
    .user_agent("my-service/1.0")
    .build()?;

let resp = client.post("https://api.example.com/ingest")
    .json(&payload)
    .send()
    .await?;
```

**The cost of batteries:** reqwest pulls in tokio, hyper, rustls, and a long dependency chain. On a cold build, adding reqwest can mean compiling 200+ crates and several minutes. It also uses `unsafe` internally (as does most of the async ecosystem), so it is not the choice for projects that want a strict no-`unsafe` policy. As of 0.13, reqwest continues to track the current Rust edition and has mature WASM support, so you can share client code between server and browser targets. If you need observability, reqwest integrates cleanly with the [tracing ecosystem](https://github.com/tokio-rs/tracing) — see our [Rust logging libraries comparison](../2026-07-27-rust-logging-libraries-env-logger-log4rs-tracing-slog/) for how to wire tracing spans around outbound calls.

## hyper: The Foundation Layer

hyper is not an HTTP client in the "fetch this URL" sense — it is *an HTTP library for Rust*, the low-level protocol implementation that powers axum, warp, and reqwest itself. Its README is explicit about this: "If you are looking for a convenient HTTP client, then you may wish to consider reqwest." hyper gives you HTTP/1 and HTTP/2, client and server APIs, and a reputation for being "leading in performance" and "tested and correct."

What makes hyper different is that you assemble connections yourself. The official multi-server example shows the shape of it — you bind a TCP listener, then serve each connection with a service function:

```rust
use std::net::SocketAddr;
use bytes::Bytes;
use http_body_util::Full;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper::{Request, Response};
use tokio::net::TcpListener;

async fn index(_: Request<hyper::body::Incoming>) -> Result<Response<Full<Bytes>>, hyper::Error> {
    Ok(Response::new(Full::new(Bytes::from("The 1st service!"))))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let addr: SocketAddr = ([127, 0, 0, 1], 1337).into();
    let listener = TcpListener::bind(addr).await?;

    loop {
        let (stream, _) = listener.accept().await?;
        tokio::task::spawn(async move {
            if let Err(err) = http1::Builder::new()
                .serve_connection(stream, service_fn(index))
                .await
            {
                println!("Error serving connection: {:?}", err);
            }
        });
    }
}
```

Notice what hyper forces you to think about: the listener, the accept loop, the per-connection task, the body type (`Full<Bytes>`), the service function signature. That is the price of a foundation layer — and the reason the ecosystem built axum on top of it. If you are writing an application, you almost certainly want the framework, not the foundation. Our [Rust web frameworks comparison](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/) covers axum, Actix-web, and Rocket, all of which layer their own ergonomics over protocol work like this.

The payoff for using hyper directly is control: full duplex streaming, custom connection handling, HTTP/2 multiplexing, and the ability to build proxies and gateways that no higher-level client can express. This is also where hyper's client API shines — `hyper::Client` gives you a connection pool with none of reqwest's conveniences, which is exactly what a proxy author wants.

## ureq: The Minimal Blocking Client

ureq's pitch fits in one line: *"a simple, safe HTTP client"* — blocking I/O, pure Rust, and it forbids `unsafe` code entirely. There is no tokio, no async runtime, no futures; just `ureq::get(...).call()`. For a CLI tool that fetches a status endpoint or a build script that downloads a file, that simplicity is the whole point: compile time drops from minutes to seconds and the dependency tree stays tiny.

The current 3.x API, straight from the official README:

```rust
let body: String = ureq::get("http://example.com")
    .header("Example-Header", "header value")
    .call()?
    .body_mut()
    .read_to_string()?;
```

For anything beyond one-off calls, you create an `Agent`, which holds a connection pool and a cookie store. Agents are cheap to clone (they wrap an `Arc`) and all clones share state, which makes them natural to pass around a CLI application:

```rust
use ureq::Agent;
use std::time::Duration;

let mut config = Agent::config_builder()
    .timeout_global(Some(Duration::from_secs(5)))
    .build();

let agent: Agent = config.into();

let body: String = agent.get("http://example.com/page")
    .call()?
    .body_mut()
    .read_to_string()?;

// Reuses the connection from the previous request.
let response: String = agent.put("http://example.com/upload")
    .header("Authorization", "example-token")
    .send("some body data")?
    .body_mut()
    .read_to_string()?;
```

With the `json` feature enabled, ureq can also serialize and deserialize typed payloads — the pattern mirrors serde's `Serialize`/`Deserialize` derives, with `send_json` and `read_json` replacing the manual body handling above. Note one behavioral difference that surprises newcomers: by default, ureq returns `Err(Error::StatusCode(code))` for any 4xx or 5xx response. You can opt out with `http_status_as_error()` if you need to inspect error bodies, but the default is opinionated — errors are errors.

ureq's blocking model is not a performance penalty in disguise; it simply offloads concurrency to threads instead of an async runtime. Spawn a thread per task and ureq keeps up fine for I/O-bound workloads. Where it genuinely struggles is high-concurrency, connection-heavy server scenarios — that is async territory. For everything else, it is the least surprising HTTP client in Rust.

## Migration and Coexistence Strategies

Moving between these crates is less painful than you might fear, because they share a common heritage: reqwest uses hyper internally, and all three expose response bodies as byte streams. A few practical notes from real migrations:

**From ureq to reqwest:** the changes are mechanical. `ureq::get(url).call()?` becomes `reqwest::get(url).await?`, and you must add `tokio` plus `#[tokio::main]` to your entrypoint — that is the biggest structural cost, because your whole call stack becomes async. Plan the async boundary first, then port call sites one at a time; `reqwest::blocking` exists as a stopgap if you want to keep sync signatures while migrating.

**From reqwest to hyper:** only do this if you are extracting a library or building a proxy. You are trading convenience for control, which means re-implementing redirects, cookies, and JSON handling yourself. Keep reqwest for the code paths that need it and use hyper only for the hot path — many production systems run both crates in one binary without conflict, since reqwest already depends on hyper.

**Version pinning:** hyper 1.x is a stable API that will not break — the 1.0 release in 2024 was a deliberate "this is done changing" statement, and hyper 2.x is a separate crate (`hyper-util` carries the async glue). Pin `reqwest = "0.13"` and `ureq = "3"` in your lockfile and you are safe for the next few years. If you see tutorials using the old hyper 0.14 `Client::new()` API, they are outdated — the 1.x `service_fn` + `http1::Builder` pattern above is current.

**TLS decisions matter more than the client:** all three support rustls and native-tls, but the choice changes your dependency tree and your platform story. rustls is pure Rust, easier to cross-compile, and the default for both reqwest and ureq. native-tls gives you the system certificate store (useful behind corporate MITM proxies). For more on the TLS layer itself, our [TLS implementation libraries guide](../2026-06-21-tls-ssl-implementation-libraries-openssl-boringssl-libressl-rustls/) covers the trade-offs in depth.

**Benchmark before you optimize:** if you are choosing between async and blocking clients for throughput reasons, measure first — hyper and reqwest both post strong numbers, and for most services the bottleneck is the upstream API you are calling, not your client. Our [Rust benchmarking guide](../2026-07-31-rust-benchmarking-criterion-iai-divan/) shows how to set up criterion benchmarks that will actually tell you whether the client matters.

## Common Pitfalls and Performance Traps

**1. Building a new `Client` per request.** reqwest and hyper pool connections; constructing a client inside a loop throws the pool away every iteration and you lose keep-alive entirely. Build once, share via `Arc` or a service struct.

**2. Blocking inside async code.** Calling `ureq::get(...)` (or `reqwest::blocking`) inside an async task blocks the runtime worker thread. Use `tokio::task::spawn_blocking` if you must mix, or go async end-to-end.

**3. Assuming ureq follows all redirects.** ureq follows redirects for GET by default, but redirect behavior for POST and other methods differs from reqwest's fully configurable `Policy`. Test your actual endpoint sequence.

**4. Ignoring the default error-on-4xx behavior.** ureq's `Error::StatusCode` default catches people who previously read error bodies from `reqwest::Error::status()`. Check which error variant you are matching on after a migration.

**5. Forgetting the `json` feature flag.** `send_json`/`read_json` in ureq and `reqwest::Client::json()` both require the `json` feature; without it you get confusing "method not found" errors. In reqwest, `json` is off by default.

**6. Compile-time regression in CI.** Adding tokio + reqwest can push a small project's clean-build time from seconds to minutes. If CI builds every commit from scratch, consider caching the target directory or moving the client into a workspace crate that changes less often.

**7. Cookie store surprises.** ureq's `cookies` feature is off by default; reqwest's cookie store is opt-in via `Client::builder().cookie_store(true)`. If your integration tests depend on session cookies, enable it explicitly or you will see 401s that make no sense.

## FAQ

**Is reqwest built on top of hyper?**
Yes. reqwest's async client uses hyper for the HTTP/1.1 and HTTP/2 protocol layers and adds convenience on top: JSON, cookies, redirects, proxies, and TLS configuration. This is why the dependency trees of reqwest and hyper overlap heavily, and why the two crates coexist cleanly in one binary.

**Can ureq be used in a tokio async application?**
You can call it from `spawn_blocking`, but ureq is designed for blocking contexts. Mixing it into async code directly blocks a runtime worker, so for async applications the idiomatic choice is reqwest or hyper.

**Which Rust HTTP client is fastest?**
For raw protocol throughput, hyper leads benchmarks — it is the foundation used by the fastest frameworks. In practice, application-level latency is dominated by connection reuse and TLS session resumption, which reqwest and hyper both handle well. Measure your workload before optimizing; the differences are usually small relative to upstream API latency.

**Does reqwest support WASM?**
Yes. reqwest has official WASM support and can run in browsers and edge runtimes, which makes it the only one of the three with a real client-side story. ureq and hyper target native platforms.

**Is hyper 2.x a drop-in replacement for hyper 1.x?**
No — hyper 2.x is a separate crate with a different API (the async glue moved to `hyper-util`). hyper 1.x remains the stable, supported foundation and is what reqwest and axum currently build on. Pin your versions and upgrade deliberately.

**Which client should I use for a CLI tool?**
ureq. Blocking reads are natural in command-line programs, the compile time is seconds rather than minutes, and the no-`unsafe` implementation keeps the binary small and auditable.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust HTTP Clients in 2026: reqwest vs hyper vs ureq — Which Should You Use?",
  "description": "Compare reqwest, hyper, and ureq for Rust HTTP clients in 2026: features, performance, TLS options, code examples, migration strategies, and a use-case decision matrix.",
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

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
