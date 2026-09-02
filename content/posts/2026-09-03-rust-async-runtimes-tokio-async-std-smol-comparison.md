---
title: "Tokio vs async-std vs smol in 2026: Choosing the Right Rust Async Runtime"
date: "2026-09-03"
tags: ["rust", "async", "concurrency", "developer-tools"]
draft: false
---

Every serious Rust project eventually hits the same fork in the road: which async runtime do you build on? The decision is nearly irreversible — your runtime shapes your dependency tree, your concurrency primitives and even which libraries you are allowed to use, since `reqwest`, `tonic` and most of the database drivers assume one specific runtime. In 2026 the three candidates have diverged sharply: **Tokio (33,059 stars)** dominates production, **smol (5,056 stars)** thrives as a featherweight alternative, and **async-std (4,065 stars)** has effectively stopped evolving. This guide gives you the maintenance facts, the scheduler details and a decision matrix so you pick once and pick right.

## TL;DR: Quick Verdict

Building a **network service, web API or anything that will share data across threads**? Use **Tokio** — its multi-threaded work-stealing scheduler, batteries (timers, filesystem, signals, channels) and ecosystem dominance (hyper, axum, reqwest, tonic all assume Tokio) make it the default for a reason. Building a **small tool, embedded runtime or dependency-light library** where you just need `async` without ceremony? Use **smol** — one tiny crate, no macros, no feature flags. Do not start new projects on **async-std**: its last meaningful activity was 2025 and the ecosystem moved on; migrate existing async-std code to Tokio incrementally.

## Quick Comparison Table

GitHub data fetched 2026-09-03. All three are MIT/Apache-2.0 dual-licensed.

| Dimension | Tokio | async-std | smol |
|---|---|---|---|
| GitHub stars | 33,059 | 4,065 | 5,056 |
| Last commit | 2026-08-31 | 2025-08-15 | 2026-08-03 |
| Current version | 1.x (mature) | 1.13.x | 2.x |
| Scheduler | Multi-threaded, work-stealing | Multi-threaded via `task::spawn` on a thread pool | Work-stealing executors (`async-executor`) |
| Entry macro | `#[tokio::main]` | `#[async_std::main]` | None needed (`smol::block_on`) |
| Built-in I/O | Net, fs, time, signal, process, sync primitives | Net, fs, time (std-mirroring API) | Async I/O via `async-io`; time via `async-io`/`futures-lite` |
| Channels | mpsc, oneshot, watch, broadcast | mpsc, oneshot (std-mirroring) | `async-channel` (separate crate) |
| io_uring support | Yes (`tokio-uring`) | No | No |
| Macro dependency | Required (`#[tokio::main]`) | Required (`#[async_std::main]`) | None |
| Ecosystem fit | hyper, axum, reqwest, tonic, sqlx, AWS SDK | Tide, Surf (dormant) | Any Tokio library via `async-compat` |
| Maintenance status | Very active (weekly commits) | Effectively dormant since 2025 | Active, small maintainer team |
| Best for | Production services, web, data pipelines | Legacy async-std codebases | Minimal deps, embedding, teaching |

## Scenario Decision Matrix

| Your situation | Recommended runtime | Why |
|---|---|---|
| Public web API or microservice in production | Tokio | axum/hyper/reqwest/tonic all assume Tokio; you avoid compatibility shims entirely |
| High-throughput proxy, gateway or message broker | Tokio | Multi-threaded work-stealing scheduler plus `tokio-uring` for io_uring-backed I/O |
| CLI tool that needs a little concurrency | smol | One crate, no proc macros, compiles fast; `smol::block_on` is all you need |
| Embedding a runtime inside a larger application | smol | Tiny footprint and no required macros make it unobtrusive as a library dependency |
| Maintaining a legacy async-std application | Tokio (migrate) | async-std is dormant; port task spawning and I/O to Tokio while keeping business logic intact |
| Library crate that must not force a runtime on users | smol (or none) | Keep your crate runtime-agnostic; smol works where callers bring their own executor |

## Tokio — The Production Default

Tokio is the reason Rust async succeeded. It pairs a multi-threaded work-stealing scheduler with a full battery of I/O primitives — TCP/UDP, timers, filesystem, signals, process management, and mpsc/oneshot/watch/broadcast channels — behind a single `#[tokio::main]` macro. The ecosystem built on top (hyper, axum, reqwest, tonic, sqlx, the AWS SDK) makes Tokio the path of least resistance for any networked service.

```toml
[dependencies]
tokio = { version = "1", features = ["full"] }
```

```rust
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() {
    // Spawn a task onto the multi-threaded runtime
    let handle = tokio::spawn(async {
        sleep(Duration::from_millis(100)).await;
        println!("background task finished");
    });

    sleep(Duration::from_millis(50)).await;
    println!("main task continuing...");
    let _ = handle.await;
}
```

Tokio's real advantage is operational: `tokio::select!` for racing futures, `spawn_blocking` for CPU-heavy work, graceful shutdown via cancellation tokens, and `tokio-console` for inspecting task state in production. Its costs are real but predictable: a larger dependency tree (enabled by feature flags — use `features = ["rt-multi-thread", "macros", "time"]` instead of `"full"` if you care), proc-macro entry points, and a learning curve around `Send` bounds and runtime handles. If you are building anything that lives on a network, this is the safe choice — the Rust community's consensus for six straight years.

## smol — Async Without the Ceremony

smol answers a simple question: what if async I/O did not require a framework? It is a collection of tiny crates — `async-executor`, `async-io`, `async-channel`, `async-lock`, `async-task`, `blocking`, `futures-lite` — coordinated by a one-file runtime that needs no macros and no feature flags.

```toml
[dependencies]
smol = "2"
```

```rust
use smol::future;

fn main() {
    smol::block_on(async {
        // Spawn a task on the default executor
        let task = smol::spawn(async {
            println!("hello from a smol task");
            1 + 2
        });

        // Await its output
        assert_eq!(future::block_on(task), 3);
    });
}
```

Because smol is just a library, it compiles quickly, stays out of your type signatures and works when you need to run async code inside an application that already owns its threads. Projects that want the Tokio ecosystem without adopting Tokio itself use the `async-compat` crate, which lets Tokio-based libraries (including `reqwest` and `hyper`-derived clients) run inside smol's executor. The trade-offs: no io_uring integration, a smaller community, and you assemble advanced pieces (timeouts, channels) from the small crates yourself. For CLIs, embedded runtimes and dependency-conscious libraries, smol is the quiet winner.

## async-std — The Dormant Contender

async-std launched in 2019 with a beautiful idea: mirror the standard library's API surface (`async_std::fs`, `async_std::net`, `async_std::task`) so async Rust feels like sync Rust. For a while it was the friendliest on-ramp to async, and it powers the Tide web framework and the Surf HTTP client.

```toml
[dependencies]
async-std = "1"
```

```rust
use async_std::task;

fn main() {
    task::block_on(async {
        let handle = task::spawn(async {
            println!("hello from an async-std task");
        });
        handle.await;
    });
}
```

The uncomfortable fact in 2026 is that async-std has been effectively dormant since 2025 — its last commit trail is sparse, Tide and Surf are likewise quiet, and the ecosystem has consolidated around Tokio. Its design goal (mirroring `std`) also proved limiting: by not offering the scheduler knobs and I/O depth of Tokio, it gave teams little reason to stay once Tokio's ergonomics caught up. If you maintain an async-std codebase, treat this as a migration prompt, not a crisis: async-std programs are small and structural, so porting `task::spawn` and I/O calls to Tokio usually takes days, not weeks. New projects should not start here.

## Common Pitfalls and Migration Traps

**Blocking the executor is the number one async bug.** Any synchronous sleep, file read or CPU loop inside an async task stalls the entire worker thread. Use `tokio::task::spawn_blocking` (or `smol::blocking!`) for blocking work, and prefer `tokio::time::sleep` over `std::thread::sleep` in async contexts.

**Do not mix runtimes in one process.** If you call `reqwest` (Tokio-based) inside a smol executor without `async-compat`, futures panic at runtime with executor mismatch errors. The same applies to passing Tokio handles into async-std contexts. Pick one runtime as your substrate and route everything else through compatibility crates.

**Feature-flag discipline in Tokio.** `features = ["full"]` compiles everything and slows your build noticeably. Production Tokio apps typically need only `rt-multi-thread`, `macros`, `time`, `net`, `sync` and `signal` — enable exactly what you use and let your editor flag missing features during development.

**`Send` bounds bite at scale.** Tokio's multi-threaded executor requires spawned tasks to be `Send`; holding non-`Send` types (raw pointers, some FFI handles, `Rc`) across an `.await` produces confusing compile errors. Learn the rule early: if a future crosses threads, everything it touches must be `Send + 'static`.

**Migration from async-std is mechanical.** Map `async_std::task::spawn` → `tokio::spawn`, `async_std::fs`/`net`/`time` → their Tokio equivalents, and replace `#[async_std::main]` with `#[tokio::main]`. Keep your business logic in plain functions that take and return owned data — then the runtime swap stays a one-week chore instead of a rewrite.

For a broader look at how Tokio compares with event-loop runtimes in other languages, see our [cross-language async I/O runtime comparison: libuv vs Boost.Asio vs Tokio](../2026-06-20-async-io-runtime-libraries-libuv-boost-asio-tokio/). If you are choosing a web framework on top of your runtime, our [Rust web frameworks guide: Actix Web vs Rocket vs Axum](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/) and [Rust HTTP client libraries: reqwest vs hyper vs ureq](../2026-08-17-rust-http-client-libraries-reqwest-hyper-ureq-comparison/) cover the layers above Tokio.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Tokio vs async-std vs smol in 2026: Choosing the Right Rust Async Runtime",
  "description": "Compare Tokio, async-std and smol in 2026: scheduler architecture, ecosystem fit, maintenance status and migration paths. Includes comparison tables, Rust code examples and async pitfalls.",
  "datePublished": "2026-09-03",
  "dateModified": "2026-09-03",
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

**What is a Rust async runtime?**
A runtime provides the executor that polls futures to completion and the I/O driver that wakes them when data is ready. Rust's standard library defines `async`/`await` but ships no executor, so every async program selects a runtime — Tokio, smol or async-std — that supplies the scheduler and I/O primitives.

**Is async-std dead in 2026?**
Effectively dormant. Its last meaningful commit activity was in 2025, and companion projects (Tide, Surf) are quiet too. It still works for existing applications, but no new ecosystem development targets it. If you are starting a project, choose Tokio or smol instead; if you maintain async-std code, plan a migration to Tokio.

**Does smol work with reqwest and other Tokio-based libraries?**
Yes, through the `async-compat` crate. Add `async-compat` and wrap your executor, and Tokio-based libraries such as `reqwest` run inside smol. The compatibility layer costs a little performance and complexity, which is why teams that mostly use the Tokio ecosystem usually adopt Tokio itself.

**When does Tokio's multi-threaded runtime actually help?**
When your workload mixes I/O waits with CPU work across many concurrent tasks, or when tasks must communicate across threads. The work-stealing scheduler keeps all cores busy. For a CLI that spawns a handful of short tasks, single-threaded `smol::block_on` is faster to write and runs identically well.

**Which runtime should a library crate use?**
Preferably none. Libraries should be runtime-agnostic by default and expose executor hooks where needed. If a library must spawn background tasks, smol's small footprint makes it the least intrusive runtime to depend on, and Tokio-based libraries document that requirement explicitly.

**How do I migrate from async-std to Tokio?**
Mechanically: replace `#[async_std::main]` with `#[tokio::main]`, map `async_std::task::spawn` to `tokio::spawn`, and swap `async_std::fs`/`net`/`time` calls for their Tokio equivalents. Keep business logic in non-async functions where possible so the port stays shallow.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
