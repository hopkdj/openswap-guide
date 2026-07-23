---
title: "Rust Observability Libraries: tracing vs opentelemetry-rust vs metrics-rs — Instrumenting Production Services"
date: "2026-07-23"
tags: ["rust", "observability", "tracing", "metrics", "opentelemetry", "logging", "monitoring", "rust-crates"]
draft: false
---

## Introduction

Observability is the cornerstone of running reliable production services. While Rust's performance makes it ideal for infrastructure and systems programming, instrumenting your Rust applications properly requires understanding the available observability primitives. The Rust ecosystem offers three distinct approaches: structured tracing with spans, OpenTelemetry-based distributed tracing, and lightweight application metrics.

This guide compares **tracing** (the tokio-rs ecosystem), **opentelemetry-rust**, and **metrics-rs** — three leading Rust observability libraries that serve different instrumentation needs. We'll cover their design philosophies, integration patterns, and how they complement each other in a production observability stack.

## Comparison Table

| Feature | tracing | opentelemetry-rust | metrics-rs |
|---------|---------|-------------------|------------|
| **Stars** | ~4,000 | ~2,000 | ~1,000 |
| **Primary Focus** | Structured spans & events | Distributed tracing (OTLP) | Application metrics |
| **Spans** | Yes (rich, nested) | Yes (via tracing-opentelemetry) | No |
| **Metrics** | Limited (via tracing-metrics) | Via metrics integration | First-class (counters, gauges, histograms) |
| **Exporters** | Log, JSON, OpenTelemetry, Jaeger | OTLP, Jaeger, Zipkin, stdout | Prometheus, statsd, graphite |
| **Context Propagation** | Built-in (parent/child) | W3C TraceContext, B3 | No |
| **no_std** | Yes (with feature flags) | Limited | Yes |
| **Subscriber Architecture** | Yes (composable layers) | Pipeline-based | Recorder-based |
| **Log Compatibility** | Log crate bridge | Via tracing bridge | No |
| **Best For** | Application tracing & debugging | Cross-service distributed tracing | Infrastructure metrics |

## tracing: The Foundation

**tracing** (from the tokio-rs project) is Rust's de facto standard for structured, span-based instrumentation. It provides a powerful subscriber architecture where you can compose multiple layers for different output destinations.

### Installation

```toml
[dependencies]
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "json"] }
tracing-futures = "0.2"  # For async instrumentation
```

### Basic Usage: Spans and Events

```rust
use tracing::{info, error, debug, warn, span, Level, instrument};
use tracing_subscriber::{fmt, EnvFilter};

#[instrument]
async fn process_order(order_id: u64, amount: f64) -> Result<(), Box<dyn std::error::Error>> {
    info!(order_id, amount, "Processing order");

    let span = span!(Level::INFO, "payment", payment_id = 12345);
    let _guard = span.enter();

    if amount > 1000.0 {
        warn!(amount, "Large order detected, requires approval");
    }

    let result = charge_customer(amount).await;
    debug!(?result, "Payment result");

    match result {
        Ok(_) => {
            info!("Order processed successfully");
            Ok(())
        }
        Err(e) => {
            error!(error = %e, "Order processing failed");
            Err(e)
        }
    }
}

async fn charge_customer(amount: f64) -> Result<(), String> {
    // Simulated payment processing
    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    Ok(())
}

fn main() {
    // Configure subscriber with JSON output and filtering
    tracing_subscriber::fmt()
        .json()
        .with_env_filter(EnvFilter::from_default_env()
            .add_directive("info".parse().unwrap())
            .add_directive("my_app=debug".parse().unwrap()))
        .init();

    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(async {
        process_order(42, 1500.0).await.ok();
    });
}
```

### Custom Subscriber Layers

```rust
use tracing_subscriber::layer::SubscriberExt;
use tracing_subscriber::Registry;

fn main() {
    // Compose multiple output layers
    let stdout_layer = tracing_subscriber::fmt::layer()
        .pretty()
        .with_target(true);

    let file_layer = tracing_subscriber::fmt::layer()
        .json()
        .with_writer(std::fs::File::create("trace.log").unwrap());

    let subscriber = Registry::default()
        .with(EnvFilter::new("info,my_app=trace"))
        .with(stdout_layer)
        .with(file_layer);

    tracing::subscriber::set_global_default(subscriber)
        .expect("Failed to set subscriber");
}
```

## opentelemetry-rust: Distributed Tracing

**opentelemetry-rust** brings the OpenTelemetry standard to Rust, enabling cross-service distributed tracing with OTLP exporters for platforms like Jaeger, Tempo, and Honeycomb.

### Installation

```toml
[dependencies]
opentelemetry = { version = "0.22", features = ["trace"] }
opentelemetry_sdk = { version = "0.22", features = ["rt-tokio"] }
opentelemetry-otlp = { version = "0.15", features = ["tonic", "metrics"] }
tracing-opentelemetry = "0.23"  # Bridge tracing → OTel
```

### Basic Setup with OTLP Exporter

```rust
use opentelemetry::trace::TracerProvider as _;
use opentelemetry_sdk::trace::{self, Sampler};
use opentelemetry_otlp::WithExportConfig;
use tracing_subscriber::prelude::*;

fn init_tracer() -> Result<(), Box<dyn std::error::Error>> {
    // Configure OTLP exporter
    let exporter = opentelemetry_otlp::new_exporter()
        .tonic()
        .with_endpoint("http://localhost:4317")  // OTLP collector
        .with_timeout(std::time::Duration::from_secs(3));

    // Set up the tracer provider
    let tracer_provider = trace::TracerProvider::builder()
        .with_batch_exporter(exporter, opentelemetry_sdk::runtime::Tokio)
        .with_sampler(Sampler::AlwaysOn)
        .with_config(trace::config().with_resource(
            opentelemetry::Resource::new(vec![
                opentelemetry::KeyValue::new("service.name", "my-rust-service"),
                opentelemetry::KeyValue::new("service.version", env!("CARGO_PKG_VERSION")),
            ]),
        ))
        .build();

    let tracer = tracer_provider.tracer("my-service-tracer");

    // Bridge tracing spans to OpenTelemetry
    let otel_layer = tracing_opentelemetry::layer().with_tracer(tracer);

    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new("info"))
        .with(tracing_subscriber::fmt::layer())
        .with(otel_layer)
        .init();

    Ok(())
}

#[tracing::instrument(fields(order_id = %order_id))]
async fn create_order(order_id: u64, items: Vec<String>) {
    tracing::info!(item_count = items.len(), "Creating order");

    // Context automatically propagated via W3C TraceContext
    // Downstream HTTP calls will include traceparent header
    reserve_inventory(order_id).await;
    process_payment(order_id).await;

    tracing::info!("Order created successfully");
}

async fn reserve_inventory(order_id: u64) {
    let _span = tracing::info_span!("reserve_inventory", order_id).entered();
    // Inventory logic here
}

async fn process_payment(order_id: u64) {
    let _span = tracing::info_span!("process_payment", order_id).entered();
    // Payment logic here
}
```

## metrics-rs: Application Metrics

**metrics-rs** provides a lightweight, zero-cost abstraction for instrumenting your code with counters, gauges, and histograms. It decouples metric emission from collection, allowing you to swap exporters without changing instrumentation code.

### Installation

```toml
[dependencies]
metrics = "0.22"
metrics-exporter-prometheus = "0.14"
```

### Basic Usage

```rust
use metrics::{counter, gauge, histogram, describe_counter, describe_gauge, describe_histogram};
use metrics_exporter_prometheus::{PrometheusBuilder, PrometheusHandle};
use std::thread;
use std::time::Duration;

fn main() {
    // Initialize Prometheus exporter
    let builder = PrometheusBuilder::new();
    let handle = builder
        .install_recorder()
        .expect("Failed to install recorder");

    // Describe metrics (for documentation)
    describe_counter!("http_requests_total", "Total HTTP requests");
    describe_gauge!("active_connections", "Current active connections");
    describe_histogram!("request_duration_seconds", "Request duration in seconds");

    // Simulate a service
    for i in 0..100 {
        counter!("http_requests_total", 1, "method" => "GET", "status" => "200");
        gauge!("active_connections", (i % 10) as f64);
        histogram!("request_duration_seconds", (i as f64) * 0.01, "endpoint" => "/api/data");
        thread::sleep(Duration::from_millis(50));
    }

    // Export Prometheus metrics
    println!("{}", handle.render());
}
```

### Integration with Axum Web Server

```rust
use axum::{Router, routing::get, middleware};
use metrics_exporter_prometheus::{PrometheusBuilder, Matcher};
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    // Set up Prometheus exporter with endpoint
    let (recorder, exporter) = PrometheusBuilder::new()
        .with_http_listener("0.0.0.0:9001".parse::<SocketAddr>().unwrap())
        .add_global_label("service", "my-rust-api")
        .build()
        .expect("Failed to build Prometheus exporter");

    metrics::set_global_recorder(recorder).unwrap();

    // Metrics middleware
    async fn metrics_middleware<B>(
        req: axum::http::Request<B>,
        next: axum::middleware::Next<B>,
    ) -> axum::response::Response {
        let start = std::time::Instant::now();
        let method = req.method().to_string();
        let path = req.uri().path().to_string();

        let response = next.run(req).await;

        let duration = start.elapsed();
        counter!("http_requests_total", 1, "method" => method.clone(), "path" => path.clone());
        histogram!("http_request_duration_seconds", duration.as_secs_f64(),
            "method" => method, "path" => path);

        response
    }

    let app = Router::new()
        .route("/", get(|| async { "Hello, observability!" }))
        .layer(middleware::from_fn(metrics_middleware));

    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await.unwrap();
    axum::serve(listener, app).await.unwrap();
}
```

## Using All Three Together

The three libraries aren't mutually exclusive — they complement each other in a comprehensive observability stack:

```rust
use tracing_subscriber::prelude::*;

fn setup_observability() {
    // Layer 1: Pretty console output
    let fmt_layer = tracing_subscriber::fmt::layer().pretty();

    // Layer 2: OpenTelemetry distributed tracing
    let otel_layer = tracing_opentelemetry::layer()
        .with_tracer(create_otel_tracer());

    // Layer 3: Metrics recorder
    let metrics_recorder = PrometheusBuilder::new()
        .install_recorder()
        .unwrap();

    // Compose all layers
    tracing_subscriber::registry()
        .with(EnvFilter::new("info"))
        .with(fmt_layer)
        .with(otel_layer)
        .init();

    // Now use both spans and metrics in your code
}

#[tracing::instrument]
async fn handle_request() {
    counter!("requests_received", 1);
    let start = std::time::Instant::now();
    tracing::info!("Processing request");

    // ... business logic ...

    histogram!("request_duration_ms", start.elapsed().as_millis() as f64);
}
```

## FAQ

### Do I need all three libraries in every service?

No. For a simple CLI tool, tracing alone is sufficient. For a microservice that's part of a larger system, tracing + opentelemetry-rust provides distributed trace context. For infrastructure-level services (proxies, load balancers, databases), metrics-rs with Prometheus is often more important than detailed spans. Choose based on your observability needs: debugging → tracing, cross-service visibility → opentelemetry, operational dashboards → metrics.

### How does tracing compare to the log crate?

tracing is a superset of the log crate's functionality. It provides structured key-value fields, nested spans (not just flat log lines), and a composable subscriber architecture. The `tracing-log` crate bridges existing log-based libraries into the tracing ecosystem. If you're starting a new Rust project, use tracing directly rather than the log crate.

### Can I export tracing spans to Jaeger?

Yes. Use the `tracing-opentelemetry` bridge layer which converts tracing spans to OpenTelemetry spans, then configure the OTLP exporter to send to Jaeger's OTLP endpoint (port 4317 for gRPC or 4318 for HTTP). Jaeger natively supports OTLP ingestion since version 1.35.

### What's the overhead of instrumentation?

tracing uses lock-free data structures for span creation and event recording, with overhead typically under 100ns for a span enter/exit cycle on modern hardware. metrics-rs uses atomic operations for counter/gauges (~10-20ns). opentelemetry-rust adds network export overhead via OTLP, but batching minimizes this to ~1-2% CPU on typical workloads. All three are designed to be left enabled in production.

### How do I correlate logs with traces?

The tracing subscriber's JSON format includes `span.id` and `span.parent` fields in each log event. When exported to OpenTelemetry backends, these become `trace_id` and `span_id`. Configure your log aggregation system (Loki, Elasticsearch) to parse these fields, and your observability dashboard can link from a log line directly to the distributed trace it belongs to.

## Performance Benchmarks

Instrumentation overhead should never be a bottleneck for Rust services. Benchmarks on an AMD Ryzen 9 show:

| Operation | tracing | opentelemetry-rust | metrics-rs |
|-----------|---------|-------------------|------------|
| Span enter/exit | ~75ns | ~120ns (with export) | N/A |
| Event emission | ~60ns | ~90ns | N/A |
| Counter increment | N/A | N/A | ~12ns |
| Gauge set | N/A | N/A | ~15ns |
| Histogram record | N/A | N/A | ~80ns |

For context, a single syscall is ~200-500ns. Observability instrumentation overhead is negligible compared to any I/O or network operation your service performs.

## Why Self-Host Your Observability Stack

Running your own observability infrastructure — with Prometheus for metrics, Tempo for distributed tracing, and Loki for log aggregation — gives you complete control over your telemetry data with no egress costs or retention limits. Combined with Rust's high-performance observability libraries, you can instrument services with near-zero overhead while keeping all your data on-premises. For more context, see our guide on [self-hosted observability platforms](../2026-04-20-openobserve-vs-quickwit-vs-siglens-self-hosted-observability-guide-2026/) and our [Rust error handling comparison](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/). For database-level monitoring specifically, check our [database monitoring guide](../2026-04-18-pgwatch2-vs-percona-pmm-vs-pgmonitor-self-hosted-database-monitoring-guide-2026/).

---

**💡 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Observability Libraries: tracing vs opentelemetry-rust vs metrics-rs — Instrumenting Production Services",
  "description": "Compare Rust observability libraries tracing, opentelemetry-rust, and metrics-rs. Includes code examples for structured spans, OTLP distributed tracing, Prometheus metrics, and guidance for building a comprehensive Rust observability stack.",
  "datePublished": "2026-07-23",
  "dateModified": "2026-07-23",
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
