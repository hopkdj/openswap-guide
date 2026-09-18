---
title: "Stop Fighting std::sync::mpsc: crossbeam-channel vs flume vs kanal in 2026"
date: "2026-09-19"
tags: ["rust", "concurrency", "developer-tools", "performance", "comparison", "guide"]
draft: false
cover: "/img/screenshots/crossbeam-channel-benchmarks.jpg"
---

# Stop Fighting std::sync::mpsc: crossbeam-channel vs flume vs kanal in 2026

`std::sync::mpsc` is the standard library's answer to message passing in Rust, and it is the first one you outgrow. It is **multi-producer, single-consumer** — a single `Receiver` that cannot be cloned. It has no `select`. It has no timed send. It has no async integration. The moment you need two worker threads draining one queue, or one thread waiting on three channels at once, you are writing your own synchronization on top of a primitive that was never meant for it.

Three crates fix this, and they have quietly diverged in 2026: **crossbeam-channel** (8,577 ★ on the parent repo, 0.5.17 released 2026-09-05) is the mature MPMC workhorse with the richest selection API; **flume** (3,075 ★, 0.12.0) is the zero-`unsafe` drop-in replacement that now sits in *documented casual maintenance mode*; **kanal** (1,768 ★, 0.2.0-beta1) is the fastest-rising challenger that unifies sync and async on one channel type — at the cost of a still-beta API.

Choosing between them is not a benchmark contest. It is a decision about who maintains your concurrency primitive for the next three years.

## TL;DR — Quick Verdict

- **Want maximum features, zero drama, and the widest ecosystem adoption?** Use **crossbeam-channel**. `bounded`, `unbounded`, `after`, `tick`, `never`, `select!`, and a dynamic `Select` builder. Version 0.5.17, MSRV 1.74, dual MIT/Apache-2.0.
- **Want a zero-`unsafe` implementation with async and select as opt-in Cargo features?** Use **flume** — but read its maintenance status first. The README states plainly that heavy feature development has stopped and only critical fixes land.
- **Want one channel type that works from both sync and async code, with the lowest per-message overhead?** Use **kanal** — if you can accept a `0.2.0-beta1` API and a much smaller community.
- **Already all-in on tokio?** `tokio::sync::mpsc` is fine for pure-async, single-consumer fan-in pipelines. It is not a general MPMC primitive, and it cannot be consumed from blocking threads without `blocking_recv`.

## Comparison Table (live repository data, September 2026)

| | crossbeam-channel | flume | kanal |
|---|---|---|---|
| **Stars (repo)** | 8,577 ★ (crossbeam-rs/crossbeam) | 3,075 ★ | 1,768 ★ |
| **Crate version** | 0.5.17 (2026-09-05) | 0.12.0 | 0.2.0-beta1 |
| **Last commit** | 2026-09-07 | 2026-08-07 | 2026-07-19 |
| **License** | MIT OR Apache-2.0 | MIT OR Apache-2.0 | MIT |
| **Rust edition / MSRV** | 2021 / 1.74 | 2018 / 1.78.0 | 2021 |
| **`unsafe` in codebase** | Yes (lock-free internals) | **None — by design** | Yes |
| **MPMC** | ✅ Sender + Receiver both cloneable | ✅ | ✅ |
| **Bounded + unbounded** | ✅ | ✅ (plus rendezvous) | ✅ (incl. zero-capacity) |
| **`select!`-style wait** | ✅ `select!` + dynamic `Select` | ✅ `Selector` (feature `select`) | ✅ `select!` |
| **Async API** | Via `crossbeam-utils` async support, not first-class | ✅ feature `async`, sync↔async mix | ✅ **unified** sync + async |
| **Timed send/recv** | ✅ `send_timeout`, `recv_timeout` | ✅ send timeouts and deadlines | ✅ |
| **Extra channels** | `after`, `tick`, `never` | — | — |
| **Maintenance signal** | Active, part of the crossbeam umbrella | **Casual maintenance mode (documented)** | Active, pre-1.0 |
| **Benchmarks published in repo** | ✅ `crossbeam-channel/benchmarks/plot.png` | ✅ `misc/benchmarks.png` | Methodology described in README |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended | Why |
|---|---|---|
| Fan-out to N workers, one shared job queue | **crossbeam-channel** | MPMC with cloneable receiver handles, no wrapper code |
| Blocking thread must wait on sockets + channels + a timer | **crossbeam-channel** | `select!` over channels, `tick()` and `after()` built in |
| Codebase forbids `unsafe` (audited/regulated crate) | **flume** | The README's central claim: no `unsafe` anywhere |
| One channel used by both a blocking producer and an async consumer | **kanal** | Sync and async APIs on the same channel object |
| Lowest-latency small-message path | **kanal** | Pointer-sized messages encoded into the pointer itself; zero heap allocation for zero-capacity channels |
| Long-lived service where the dependency will not be revisited for years | **crossbeam-channel** | The only one of the three with a fully active, multi-maintainer umbrella project |
| Pure tokio application, async-only, single consumer per stream | `tokio::sync::mpsc` | No extra dependency, integrates with `select!` and cancellation |

## crossbeam-channel — The Default Answer, For Good Reasons

crossbeam-channel describes itself as "an alternative to `std::sync::mpsc` with more features and better performance," and the feature list is the honest version: senders **and** receivers are `Clone`, there are `bounded` and `unbounded` constructors, extra channels like `after`, `never`, and `tick`, a `select!` macro that blocks on multiple operations, and a `Select` struct for selecting over a *dynamically built* list of operations — the thing you need when the number of channels is runtime data, not source code.

Its documented cloning semantics matter more than they look. Cloning a sender or receiver does **not** create a second stream of messages; it creates another handle to the same channel:

```rust
use crossbeam_channel::unbounded;

let (s1, r1) = unbounded();
let (s2, r2) = (s1.clone(), r1.clone());
let (s3, r3) = (s2.clone(), r2.clone());

s1.send(10).unwrap();
s2.send(20).unwrap();
s3.send(30).unwrap();

assert_eq!(r3.recv(), Ok(10));
assert_eq!(r1.recv(), Ok(20));
assert_eq!(r2.recv(), Ok(30));
```

The crate is explicit about disconnection too: when all senders or all receivers are dropped, the channel disconnects, no more messages can be sent, and remaining messages can still be received. `bounded(0)` gives you a rendezvous channel that only completes a send when a receiver is already waiting:

```rust
use crossbeam_channel::bounded;
use crossbeam_utils::thread::scope;

let (s, r) = bounded(0);

scope(|scope| {
    scope.spawn(|_| {
        r.recv().unwrap();
        s.send(2).unwrap();
    });

    s.send(1).unwrap();
    r.recv().unwrap();
}).unwrap();
```

**Maturity:** 0.5.17 shipped 2026-09-05, MSRV 1.74, edition 2021, dual-licensed MIT/Apache-2.0, and the repository publishes its own benchmark plots (`crossbeam-channel/benchmarks/plot.png`) rather than relying on blog numbers.

![crossbeam-channel benchmark plot from the official repository](/img/screenshots/crossbeam-channel-benchmarks.jpg "crossbeam-channel published benchmark plot, taken directly from the official repository")

**Where it hurts:** the performance comes from lock-free internals built on `unsafe`. If your environment requires an audited, `unsafe`-free dependency tree — some embedded, aerospace, and payment contexts — you have to justify it.

## flume — Zero `unsafe`, Opt-In Features, Honest Status

flume's pitch is unusually precise: a blazingly fast multi-producer, multi-consumer channel with **no `unsafe` code anywhere in the codebase**, `Sender` and `Receiver` that both implement `Send + Sync + Clone`, a synchronous API, and `async` support that can be mixed with sync code.

The README example is complete enough to ship:

```rust
use std::thread;

fn main() {
    println!("Hello, world!");

    let (tx, rx) = flume::unbounded();

    thread::spawn(move || {
        (0..10).for_each(|i| {
            tx.send(i).unwrap();
        })
    });

    let received: u32 = rx.iter().sum();

    assert_eq!((0..10).sum::<u32>(), received);
}
```

Features are opt-in, which keeps the default compile fast and the dependency surface small:

```toml
flume = { version = "0.12.0", default-features = false, features = ["async", "select"] }
```

- `spin` — spinlocks instead of OS-level primitives for specific workloads
- `select` — the `Selector` API, letting one thread wait on several channels or operations
- `async` — the async API, *including on otherwise synchronous channels*
- `eventual-fairness` — randomness in `Selector` to avoid biasing certain events

**The part most comparison articles will not tell you:** flume's own README declares the project is in [casual maintenance mode](https://casuallymaintained.tech/). Word for word, it says the crate "will continue to receive critical security and bug fixes, but heavy feature development has stopped," that the maintainer considers it "largely feature-complete," and that new features require a PR the author will review when time allows. That is not abandonment — it is a maintenance contract you can actually plan around, and it is more honest than silence.

It also publishes benchmark results from the crossbeam-channel benchmark suite (AMD Ryzen 7 3700x, 8/16 cores, Linux 5.11.2 with the bfq scheduler) in `misc/benchmarks.png`, credited back to its competitor's suite.

![flume benchmark results published in the official repository](/img/screenshots/flume-benchmarks.jpg "flume benchmark results from the official repository, generated with the crossbeam-channel benchmark suite")

**Where it hurts:** edition 2018 and MSRV 1.78.0, plus a maintenance posture that means "no new features" — including no new `Select` capabilities. If your roadmap needs channel features that do not exist today, they will not arrive.

## kanal — Unified Sync/Async, Pre-1.0

kanal is inspired by CSP (Communicating Sequential Processes) and its differentiator is architectural rather than cosmetic: it aims to unify message passing between the synchronous and asynchronous halves of Rust, so the same channel serves blocking threads and `async` tasks, and it does so with a specific allocation strategy.

From the README, its performance claims are concrete:

- **Pointer-sized messages are encoded into the pointer address itself**; larger messages are copied directly between sender and receiver stacks, similar to Go's approach. This removes unnecessary pointer dereferences and **eliminates heap allocation for zero-capacity channels**.
- It uses a purpose-tuned mutex for channel locking, and offers a `std-mutex` feature so you can use the standard library mutex instead — with the README claiming kanal still outperforms competitors with that change enabled.

The synchronous API is close to muscle memory:

```rust
// Initialize a bounded sync channel with a capacity for 8 messages
let (sender, receiver) = kanal::bounded(8);

let s = sender.clone();
std::thread::spawn(move || {
    s.send("hello")?;
    anyhow::Ok(())
});
```

**Where it hurts:** the crate's `Cargo.toml` currently declares `version = "0.2.0-beta1"` — the README still shows the older `kanal = "0.1"` snippet. Beta means API movement, and a smaller contributor base means fewer eyes on the lock-free paths. It also pulls `branches`, `cacheguard`, and `lock_api` as dependencies, which is more transitive surface than crossbeam-channel's dedicated crate.

## Pitfalls, Migration Notes, and Performance Traps

1. **`unbounded()` is a memory leak with good manners.** Unbounded channels absorb any producer burst until your RSS is gone. If producers are network-facing, use `bounded(n)` and decide explicitly what happens when the queue is full — block, drop, or shed load.
2. **`bounded(0)` deadlocks do not look like deadlocks.** A zero-capacity channel only completes a send when a receiver is already parked. If both sides send first, the program hangs with no panic and no error.
3. **Dropping every sender is the only way to end an iterator.** `rx.iter()` terminates when all senders are dropped. One leaked handle in a spawned thread keeps your worker loop alive forever. Prefer `drop(tx)` explicitly rather than relying on scope end.
4. **`select!` fairness is not guaranteed by default.** crossbeam-channel's `select!` picks a ready operation; flume offers the `eventual-fairness` feature specifically to avoid biasing certain events. If you are load-balancing, test the distribution rather than assuming round-robin.
5. **Do not `.recv().unwrap()` on a channel that can legitimately disconnect.** Shutdown closes channels first. Match on `RecvError` and treat disconnection as a normal termination signal.
6. **Mixing async and sync is where correctness dies.** flume allows sync channels to be used from async code and vice versa; blocking a runtime worker thread on `recv()` starves the executor. Use the dedicated async API (`recv_async`-style methods) or move blocking work to a blocking pool. kanal's unified API makes this easier to get right, which is exactly why people move to it.
7. **Migrating from `std::sync::mpsc` to flume is nearly mechanical, but not free of type changes.** flume's `Sender` is cloneable and its error types differ (`TrySendError`/`SendError` variants), so error-handling sites need a pass.
8. **Benchmark claims are workload claims.** Every one of these crates publishes impressive graphs; the crossbeam and flume plots measure specific message sizes and thread counts. Measure your own payload size, because small pointer-sized messages and multi-megabyte messages land in completely different regimes — and kanal explicitly optimizes for the former.

## FAQ

### Should I replace `std::sync::mpsc` with crossbeam-channel?

Yes, if you need multiple consumers, cloning handles, timeouts, or waiting on several channels at once. `std::sync::mpsc` remains serviceable for a single-consumer fan-in queue in simple applications, and it costs no dependency.

### Is flume abandoned?

No, but it is in documented casual maintenance mode. The maintainer states that critical security and bug fixes continue while heavy feature development has stopped. Treat it as feature-frozen and production-safe, and plan accordingly if you need new capabilities later.

### Is kanal faster than crossbeam-channel?

kanal's README describes a specific advantage: pointer-sized payloads are encoded into the pointer address, and zero-capacity channels avoid heap allocation — a design tuned for low-latency small messages. For large payloads, or workloads dominated by blocking semantics rather than per-message overhead, the difference shrinks and crossbeam-channel's maturity usually wins. Benchmark with your actual message size.

### Can these libraries be used together in one application?

Yes. They are independent crates with no shared runtime, so you can use crossbeam-channel for your blocking worker pool and `tokio::sync` primitives inside async tasks. The anti-pattern is bridging them badly: never block a runtime worker thread waiting on a synchronous channel without moving that wait to a blocking pool.

### Do these channels work in `no_std` or embedded targets?

Not as-is. All three rely on the standard library and OS threads. For `no_std` concurrency, look at `heapless`-style fixed-capacity queues or a runtime designed for embedded targets, and note that the async half of these crates assumes a full executor.

### What about tokio channels — do I need a third-party crate at all?

If your application is fully async, single-consumer per stream, and already on tokio, `tokio::sync::mpsc` and `tokio::sync::broadcast` cover most needs without an extra dependency. Reach for crossbeam-channel, flume, or kanal when you need true MPMC semantics, blocking-thread integration, or selection across dynamically built channel sets.

## The Verdict

Default to **crossbeam-channel**: 0.5.17, MSRV 1.74, an umbrella project that ships regularly, the richest selection API, and published benchmarks you can rerun. Choose **flume** when a dependency policy forbids `unsafe` or when you want sync and async on one type — and accept, in writing, that the feature set is frozen. Choose **kanal** for small-message, low-latency pipelines or whenever you need the same channel to serve blocking and async code, but pin your version until it leaves beta.

For related reading: our guide to [lock-free concurrent data structures](../2026-06-19-lockfree-concurrent-data-structures-crossbeam-disruptor-folly-ck/) covers the primitives underneath these channels, the [Rust task scheduling libraries comparison](../2026-09-17-rust-task-scheduling-libraries-tokio-cron-scheduler-delay-timer-clokwerk/) shows what sits on top of them, and the [Rust embedded key-value engines comparison](../2026-09-18-rust-embedded-key-value-engines-sled-redb-fjall/) applies the same maturity-versus-features analysis to storage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Stop Fighting std::sync::mpsc: crossbeam-channel vs flume vs kanal in 2026",
  "description": "Comparison of Rust channel libraries in 2026: crossbeam-channel, flume and kanal, with real code, version data, maintenance status and production pitfalls.",
  "datePublished": "2026-09-19",
  "dateModified": "2026-09-19",
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
