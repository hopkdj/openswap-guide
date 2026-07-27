---
title: "Rust Logging Libraries Compared: env_logger vs log4rs vs tracing vs slog"
date: "2026-07-27"
tags: ["rust", "logging", "observability", "debugging", "developer-tools"]
draft: false
---

When building production Rust applications, choosing the right logging framework is one of the first decisions you'll make — and it has lasting consequences for observability, debugging, and operational maturity. Rust's logging ecosystem is unique: the standard library provides no logging facilities, so the community has built a layered architecture with the `log` crate as the universal facade and multiple backend implementations beneath it.

In this guide, we compare the four most popular Rust logging backends — **env_logger**, **log4rs**, **tracing**, and **slog** — across configuration flexibility, structured logging support, async compatibility, and performance characteristics.

## The Rust Logging Architecture

Rust separates logging concerns into two layers. The **facade** (`log` crate) provides the `trace!()`, `debug!()`, `info!()`, `warn!()`, and `error!()` macros that application code calls. The **backend** (or subscriber) actually processes those log records — writing to stdout, files, syslog, or remote collectors.

```
Application Code
      │  info!("request processed")
      ▼
  ┌─────────┐
  │ log crate │  ← facade (trait-based, zero-cost when disabled)
  └─────────┘
      │  Log::log(&record)
      ▼
  ┌──────────────┐
  │ Backend       │  ← env_logger / log4rs / tracing / slog
  └──────────────┘
```

This design means you can swap backends without changing application code. Each backend brings different strengths to the table.

## Comparison Table

| Feature | env_logger | log4rs | tracing | slog |
|---------|-----------|--------|----------|------|
| GitHub Stars | 1,059 | 1,136 | 6,799 | 1,709 |
| Configuration | Environment variables | YAML/JSON config files | Code + env vars | Code-based, composable |
| Structured Logging | Limited (key=value via `env_logger` 0.11+) | Yes (pattern-based) | First-class (fields + spans) | First-class (key-value pairs) |
| Async/Await Support | Basic | Basic | Native (Span::enter) | Via AsyncDrain |
| Log Levels | Standard 5 levels | Standard + custom filters | Standard + per-span filtering | Standard + compile-time filtering |
| File Output | No | Yes (rolling files) | Via `tracing-appender` | Via `slog-async` + file drain |
| JSON Output | Via `env_logger` 0.11+ | Yes | Via `tracing-subscriber` JSON layer | Via `slog-json` |
| Learning Curve | Trivial | Moderate | Moderate-High | Moderate |
| Last Commit | Jul 2026 | Nov 2025 | May 2026 | Jun 2026 |

## env_logger: Simple and Predictable

`env_logger` is the de facto default for Rust CLI tools and small services. Configured almost entirely through the `RUST_LOG` environment variable, it's zero-config for the common case and well understood by the entire Rust ecosystem.

```toml
# Cargo.toml
[dependencies]
log = "0.4"
env_logger = "0.11"
```

```rust
use log::{info, warn, error};

fn main() {
    env_logger::init();
    
    info!("Server starting on port 8080");
    warn!("TLS certificate expires in 30 days");
    // error!("Failed to connect to database: {}", e);
}
```

Run with `RUST_LOG=info` to see info-level and above. The filter syntax supports per-module granularity: `RUST_LOG=warn,my_app::db=trace` shows only warnings globally but trace-level for the database module.

**Best for:** CLI tools, development, small services where you want zero-config logging.

## log4rs: Enterprise-Grade Configuration

`log4rs` brings Java-style logging configuration to Rust. Define appenders, encoders, and loggers in a `log4rs.yaml` file, with support for file rotation, custom patterns, and granular per-module filtering.

```toml
[dependencies]
log = "0.4"
log4rs = "1.3"
```

```yaml
# log4rs.yaml
appenders:
  stdout:
    kind: console
    encoder:
      pattern: "{d(%Y-%m-%d %H:%M:%S)} [{l}] {m}{n}"
  requests:
    kind: rolling_file
    path: "logs/requests.log"
    policy:
      trigger:
        kind: size
        limit: 10 mb
      roller:
        kind: fixed_window
        pattern: "logs/requests-{}.gz"
        count: 5

root:
  level: info
  appenders:
    - stdout

loggers:
  my_app::api:
    level: debug
    appenders:
      - requests
      - stdout
    additive: false
```

The YAML config supports hot-reloading via the `watch` feature, so changing log levels in production doesn't require a restart.

**Best for:** Long-running services, applications that need file-based logging with rotation, teams preferring declarative config.

## tracing: Structured, Async-Native Observability

`tracing` is more than a logging library — it's a structured observability framework designed for async Rust. It introduces the concept of **spans** (representing periods of time or units of work) alongside events (individual log records), making it the natural choice for async-heavy applications like web servers and stream processors.

```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
```

```rust
use tracing::{info, error, warn, span, Level, instrument};

#[instrument]
async fn process_order(order_id: u64) -> Result<(), Error> {
    info!(total_items = 3, "Processing order");
    
    for item_id in 1..=3 {
        let item_span = span!(Level::DEBUG, "item", item_id);
        let _enter = item_span.enter();
        // process individual item
    }
    
    Ok(())
}

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt()
        .json()
        .with_env_filter("info,process_order=trace")
        .init();
    
    process_order(42).await.unwrap();
}
```

The `#[instrument]` attribute automatically creates spans for each function call, capturing arguments and return values. Combined with `tracing-subscriber`'s JSON output, this produces structured logs perfect for ingestion into systems like OpenTelemetry collectors.

**Best for:** Async services, microservices, applications that need distributed tracing and structured observability.

## slog: Composable and Extensible

`slog` takes a functional, composable approach to structured logging. Everything is built from **drains** — composable log processing pipelines. Each drain can filter, transform, or route log records independently.

```toml
[dependencies]
slog = "2.7"
slog-term = "2.9"
slog-async = "2.8"
slog-json = "2.6"
```

```rust
use slog::{info, o, Drain, Logger};

fn main() {
    let decorator = slog_term::TermDecorator::new().build();
    let drain = slog_term::FullFormat::new(decorator).build().fuse();
    let drain = slog_async::Async::new(drain).build().fuse();
    
    let logger = Logger::root(drain, o!("version" => env!("CARGO_PKG_VERSION")));
    
    info!(logger, "server started"; "port" => 8080, "workers" => 4);
}
```

`slog`'s strength lies in its composability. You can chain drains to simultaneously write to stdout, a file, and a remote collector — each with different filtering rules — without coupling the configuration.

**Best for:** Applications needing multiple log outputs with different formats, teams that value composability and functional design patterns.

## Performance Considerations

All four backends use the `log` crate's compile-time filtering, meaning disabled log levels are compiled away to zero-cost. At the backend level:

- **env_logger** has the lowest overhead for simple stdout logging, as it does minimal processing.
- **tracing** adds overhead for span management but amortizes well in async contexts where spans accurately model the call tree.
- **slog** with async drain is highly efficient — log calls return immediately while processing happens on a separate thread.
- **log4rs** file I/O can be a bottleneck without async configuration; use the `buffer_size` parameter to batch writes.

For most applications, the performance difference is negligible compared to I/O and network latency. Profile before optimizing.

## Why Self-Host Your Logging Infrastructure?

While cloud logging services offer convenience, self-hosting your logging pipeline gives you complete control over data residency, retention policies, and costs. Rust's ecosystem integrates well with self-hosted observability stacks: `tracing` natively supports OpenTelemetry export to self-hosted collectors like Grafana Tempo and Jaeger. Log output from `env_logger` and `log4rs` can be shipped to self-hosted Elasticsearch or Loki instances via Filebeat or Promtail.

For complete observability coverage, see our [Rust web frameworks comparison](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/) and our [Rust database libraries guide](../2026-06-23-rust-database-libraries-diesel-seaorm-rusqlite/). If you're building monitoring dashboards, our [Python benchmarking tools guide](../2026-07-02-python-benchmarking-pytest-benchmark-codspeed-pyperf-asv/) covers tools for measuring Rust service performance.

## Deployment Patterns: Logging in Docker and Kubernetes

Running Rust services in containers changes logging requirements. In Docker and Kubernetes, the best practice is to log to stdout and let the container runtime handle log aggregation. Here's how each library handles containerized deployments:

**env_logger** is the simplest fit: it writes to stderr by default, which Docker captures automatically. No configuration needed beyond `RUST_LOG=info` as an environment variable in your Docker Compose or Kubernetes manifest. For Kubernetes, add a `RUST_LOG` env var to your deployment spec and logs flow to `kubectl logs` and your cluster's logging backend.

**log4rs** in containers requires careful path management. The YAML config file path needs to be available inside the container — typically mounted via ConfigMap in Kubernetes. File-based appenders should write to `/dev/stdout` in Docker rather than disk paths to avoid filling the container filesystem.

**tracing** integrates directly with OpenTelemetry collectors. In Kubernetes, deploy an OpenTelemetry Collector as a DaemonSet and configure `tracing-opentelemetry` to export spans via gRPC. This provides distributed tracing across microservices with minimal application code changes.

**slog** with async drains offers the best throughput in containerized environments. The async drain buffers log records and flushes them to stdout, preventing I/O from blocking the main event loop during traffic spikes — important for Rust services handling thousands of requests per second.

For production observability, pair your logging backend with a metrics library like `metrics-rs` for structured metrics export, and use `tokio-console` for async task introspection during development.

## Migration Path: From env_logger to tracing

Most Rust projects start with `env_logger` and migrate to `tracing` as observability requirements grow. The migration is gradual because `tracing` provides a `log` compatibility layer. Here's the step-by-step approach:

1. **Add tracing alongside env_logger**: Include both crates. Use `tracing-log` to capture `log` crate events as tracing events. This means all existing `info!()` calls appear in tracing's structured output.

2. **Convert critical paths first**: Identify your most important code paths — request handlers, database calls, external API calls — and convert them from `log::info!()` to `tracing::info!()` with structured fields. Add `#[instrument]` attributes to generate spans automatically.

3. **Swap the subscriber**: Once your critical paths use tracing natively, replace the `env_logger` init with a `tracing-subscriber` that includes both the `log` compatibility layer and your desired output format (JSON for production, pretty for development).

4. **Remove env_logger**: After all code uses tracing macros, remove the `env_logger` dependency and the `log` compatibility layer. Your code now has full structured observability with no breaking changes along the way.

This incremental approach avoids the risk of a big-bang migration and lets you ship observability improvements continuously.

## FAQ

### Which Rust logging backend should I use for a new project?

Start with `env_logger` for simplicity, then migrate to `tracing` if you need structured logging or async span tracking. `log4rs` is best when you need file-based configuration that operations teams can modify without code changes. `slog` shines when you need multiple output formats simultaneously.

### Can I use multiple logging backends at the same time?

Not directly — the `log` crate only supports one global logger. However, `tracing` can bridge to the `log` crate via `tracing-log`, letting you use `tracing` subscribers while application code calls `log` macros. Similarly, `slog` provides a `log` adapter.

### Is tracing only for async Rust?

No — `tracing` works perfectly well in synchronous code. It does add value in async contexts where spans track the call tree across `.await` points, but for synchronous applications it's essentially a structured logger with more features than `env_logger`.

### How do I add OpenTelemetry export to my Rust logs?

Use the `tracing-opentelemetry` crate to bridge `tracing` spans and events to OpenTelemetry. For the `log` crate, use the `opentelemetry-appender-log` crate. Both work with the OpenTelemetry Collector, which you can self-host for complete data ownership.

### What's the difference between tracing spans and log scopes?

Tracing spans are structured, nestable, and can carry arbitrary key-value data. Log scopes (available in some backends) are typically just string-based contextual prefixes. Tracing spans can be sampled, filtered, and exported to distributed tracing systems — log scopes cannot.
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Logging Libraries Compared: env_logger vs log4rs vs tracing vs slog",
  "description": "Comprehensive comparison of Rust logging backends — env_logger, log4rs, tracing, and slog — covering configuration, structured logging, async support, and deployment patterns in containers.",
  "datePublished": "2026-07-27",
  "dateModified": "2026-07-27",
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
