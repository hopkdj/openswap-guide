---
title: "Rust Error Handling Libraries: anyhow vs thiserror vs eyre — A Practical Guide"
date: "2026-06-22"
tags: ["rust", "error-handling", "libraries", "comparison", "systems-programming"]
draft: false
---

## Introduction

Error handling is one of Rust's defining features — the `Result<T, E>` type, the `?` operator, and the `Error` trait form a type-safe alternative to exceptions. But writing custom error types for every module quickly becomes tedious. This is where Rust's error-handling ecosystem steps in.

Three libraries dominate: **anyhow** (6,568⭐) for application-level error management, **thiserror** (5,458⭐) for library-level error definitions, and **eyre** (1,750⭐) for colorful, context-rich error reporting. All three were created by David Tolnay — the same author behind `serde`, `syn`, and `quote` — ensuring exceptional code quality and long-term maintenance.

This guide compares each library with real-world code examples and explains when to use which.

## Library Comparison

| Aspect | anyhow (6,568⭐) | thiserror (5,458⭐) | eyre (1,750⭐) |
|--------|------------------|---------------------|---------------|
| **Purpose** | Application error handling | Library error type derivation | Rich error reporting |
| **Error Type** | `anyhow::Error` (opaque) | Custom `enum` via `#[derive(Error)]` | `eyre::Report` (opaque) |
| **Type Erasure** | Yes — erases concrete types | No — preserves concrete types | Yes — erases concrete types |
| **Backtrace** | Via `std::backtrace::Backtrace` | Not built-in | Via `color-eyre` integration |
| **Context** | `.context("message")` | Manual `#[error("...")]` | `.wrap_err("message")` |
| **Downcasting** | `.downcast_ref::<T>()` | Direct pattern matching | `.downcast_ref::<T>()` |
| **no_std Support** | Optional (feature flag) | Yes (core library) | No (requires std) |
| **Crate Weight** | Light (~200 LoC impl) | Derive macro (~300 LoC) | Light + color-eyre dep |
| **Maintainer** | dtolnay (serde author) | dtolnay (serde author) | yaahc / community |

## Getting Started

**Cargo.toml:**
```toml
[dependencies]
anyhow = "1.0"
thiserror = "2.0"
eyre = "0.6"
```

**Basic Usage — anyhow:**
```rust
use anyhow::{Context, Result};
use std::fs;

fn read_config() -> Result<String> {
    let path = "config.toml";
    let content = fs::read_to_string(path)
        .with_context(|| format!("Failed to read config from {}", path))?;
    Ok(content)
}

fn main() -> Result<()> {
    let config = read_config()?;
    println!("Config loaded: {} bytes", config.len());
    Ok(())
}
```

The `anyhow::Result<T>` is a type alias for `Result<T, anyhow::Error>`. The `?` operator automatically converts any `std::error::Error` implementor into an `anyhow::Error`. The `.context()` and `.with_context()` methods attach human-readable messages to the error chain, making it easy to trace exactly where a failure occurred.

**Basic Usage — thiserror:**
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum DataStoreError {
    #[error("database connection failed: {0}")]
    ConnectionFailed(#[source] sqlx::Error),

    #[error("record not found: id={id}")]
    NotFound { id: u64 },

    #[error("validation error on field `{field}`: {message}")]
    ValidationError { field: String, message: String },

    #[error("unknown data store error")]
    Unknown,
}

// Library consumers can pattern-match on specific errors
fn handle_error(err: DataStoreError) {
    match err {
        DataStoreError::NotFound { id } => {
            log::warn!("Cache miss for record {}", id);
        }
        DataStoreError::ConnectionFailed(_) => {
            log::error!("Database unreachable, retrying...");
        }
        _ => log::error!("{}", err),
    }
}
```

`thiserror` uses a derive macro to implement `std::fmt::Display` and `std::error::Error` for your custom error enum. The `#[error("...")]` attribute defines the human-readable message, and `#[source]` marks the underlying cause for error chain traversal.

**Basic Usage — eyre:**
```rust
use eyre::{eyre, Result, WrapErr};

fn load_user(id: u64) -> Result<User> {
    let raw = std::fs::read_to_string("users.json")
        .wrap_err("failed to open users database")?;

    let users: Vec<User> = serde_json::from_str(&raw)
        .wrap_err_with(|| format!("invalid JSON in users database"))?;

    users.into_iter()
        .find(|u| u.id == id)
        .ok_or_else(|| eyre!("user {} not found", id))
}
```

`eyre` is similar to `anyhow` but adds `color-eyre` integration for beautifully formatted error output with syntax-highlighted source snippets. Install `color-eyre` and call `color_eyre::install()?` at the top of `main()` for automatic error display enhancement — no code changes needed in your error handling logic.

## When to Use Each

**Use thiserror when:**
- You're building a library crate that other developers will depend on
- Callers need to match on specific error variants
- You want to implement `Error` for custom error types without boilerplate
- You're writing `no_std` embedded firmware

**Use anyhow when:**
- You're building an application (binary crate) — error types don't need to be public
- You want to quickly propagate errors with context without defining error enums
- Your `main()` returns `Result<(), anyhow::Error>` — this is the idiomatic Rust application pattern

**Use eyre when:**
- You want rich, colorized error output in CLI tools
- You're building developer-facing tooling where error readability matters
- You need `anyhow`-style convenience with the option of `color-eyre` formatting

## Real-World Patterns

**Combining anyhow and thiserror** — the most common pattern in the Rust ecosystem: libraries define errors with `thiserror`, applications consume them with `anyhow`.

```rust
// library/src/lib.rs — uses thiserror
#[derive(Error, Debug)]
pub enum DbError {
    #[error("connection refused: {0}")]
    Connection(String),
}

// app/src/main.rs — uses anyhow
use anyhow::Result;
use my_library::DbError;

fn main() -> Result<()> {
    let conn = connect().map_err(|e: DbError| anyhow::anyhow!("startup failed: {}", e))?;
    Ok(())
}
```

**Attaching context chains with anyhow:**
```rust
fn process_order(order_id: u64) -> anyhow::Result<Order> {
    let raw = fetch_from_queue(order_id)
        .context("failed to fetch order from queue")?;

    let parsed: Order = serde_json::from_str(&raw)
        .context("order JSON is malformed")?;

    validate_order(&parsed)
        .context("order validation failed")?;

    Ok(parsed)
}
```

Each `.context()` call adds a new layer to the error chain. When this function fails, the error output shows a stack of contextual messages — from the outermost "order validation failed" down to the root cause, making debugging vastly easier than a single opaque error string.

## Why Self-Host Your Error Handling Strategy

Error handling is often treated as an afterthought in application development — but for self-hosted services running in production, a well-structured error reporting system is the difference between debugging an incident in 5 minutes versus 5 hours. When your [self-hosted error tracking platform](../self-hosted-error-tracking-sentry-alternatives-guide/) captures an error trace, the quality of the error message directly determines how quickly you can identify the root cause.

Rust's error handling libraries are particularly important for self-hosted infrastructure. When you're running a [self-hosted Rust crate registry](../2026-06-16-self-hosted-rust-crate-registries-kellnr-alexandrie-panamax/) or building [self-hosted debugging infrastructure](../2026-06-07-self-hosted-jtag-swd-remote-debug-servers-openocd-pyocd-probe-rs/) for embedded systems, every `anyhow::Error` you propagate with a `.context()` call adds actionable diagnostic information. A `"connection refused"` error is nearly useless — but `"connection refused: failed to fetch user 42 from cache backend at 10.0.1.5:6379"` tells you exactly which service, which record, and which endpoint failed.

For teams building [self-hosted build performance analytics](../2026-06-18-self-hosted-build-performance-analytics-ci-pipeline-metrics/) that process thousands of compilation events, eyre's color-formatted error output in CI logs makes failure triage dramatically faster. The difference between a plain rustc error and an eyre-wrapped error with source snippets is the difference between scrolling through 500 lines of raw output and immediately seeing the offending line of code.

## Performance and Compile-Time Considerations

A common concern with error handling libraries is the impact on compile times and binary size. All three libraries are lightweight — `anyhow` and `thiserror` are maintained by the same author and share no significant dependencies. A typical `anyhow` import adds approximately 150 KB to the final binary (stripped release build). `thiserror`'s derive macro adds negligible runtime overhead since all code generation happens at compile time — the generated `Display` and `Error` implementations are equivalent to hand-written code.

The choice between type-erased errors (`anyhow::Error`, `eyre::Report`) and concrete error enums (`thiserror`) has implications for binary size and branch prediction. Type-erased errors store the original error on the heap behind a `Box<dyn Error>`, adding one allocation per error. For applications where errors are rare (the happy path succeeds 99.9% of the time), this allocation cost is irrelevant. For high-frequency error paths — such as parsers that expect and handle malformed input on every other line — a concrete `thiserror` enum avoids the allocation entirely.

eyre's `color-eyre` integration adds approximately 300 KB to the binary from the `owo-colors`, `backtrace`, and ANSI formatting dependencies. For CLI tools distributed as single binaries, this overhead is acceptable; for embedded or WebAssembly targets, prefer `thiserror` or `anyhow` without features.


## FAQ

### Can I use anyhow in a library crate?

It's technically possible but strongly discouraged. Libraries should expose typed errors that callers can match on. `anyhow::Error` is an opaque type — downstream consumers cannot distinguish between a "not found" error and a "permission denied" error without fragile string matching. Use `thiserror` for libraries, `anyhow` for binaries.

### What's the difference between .context() and .wrap_err()?

They're semantically identical from different crates. `anyhow` uses `.context()` / `.with_context()`, while `eyre` uses `.wrap_err()` / `.wrap_err_with()`. Both attach a human-readable message to the error chain. `eyre` also provides `.suggestion()` and `.note()` methods for additional structured context.

### Do I need both anyhow and thiserror in the same project?

Many large Rust projects use both: `thiserror` in library crates for typed error definitions, and `anyhow` in the binary crate for application-level error propagation. This is the recommended pattern in the Rust community and is used by tools like `cargo`, `rust-analyzer`, and `tokio-console`.

### How does eyre compare to anyhow for CLI tools?

eyre with `color-eyre` provides significantly better error output for CLI applications — you get colorized error messages, source-code snippets pointing to the exact line where the error originated, and structured suggestions. The tradeoff is a heavier dependency tree. For a simple script, `anyhow` is sufficient; for a polished CLI tool users interact with daily, `eyre` is worth the extra dependency weight.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Error Handling Libraries: anyhow vs thiserror vs eyre — A Practical Guide",
  "description": "Complete comparison of Rust's top error handling libraries — anyhow for applications, thiserror for libraries, and eyre for rich diagnostics. Code examples and best practices.",
  "datePublished": "2026-06-22",
  "dateModified": "2026-06-22",
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
