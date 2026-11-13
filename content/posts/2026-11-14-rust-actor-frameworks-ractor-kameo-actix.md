---
title: "Rust Actor Frameworks in 2026: ractor vs Kameo vs Actix Compared"
date: "2026-11-14"
tags: ["rust", "actor-model", "concurrency", "developer-tools"]
draft: false
cover: "/img/screenshots/kameo-banner.jpg"
description: "A hands-on comparison of ractor, Kameo, and Actix for building actor-based Rust services in 2026 — real code, real download counts, and the supervision traps that bite in production."
---

# Rust Actor Frameworks in 2026: ractor vs Kameo vs Actix Compared

You picked Rust because you wanted predictable performance under concurrency. Then you hit the part nobody warns you about: the borrow checker does not give you a supervision tree. Once a `tokio::spawn` task panics, the state it owned is gone, and the task that depended on it is now waiting on a channel that will never receive another message. That gap — fault isolation with recovery, not just threads — is exactly what an actor framework brings to a Rust service.

Three frameworks own this space in 2026, and they are not interchangeable: **ractor** (a faithful Erlang `gen_server` port), **Kameo** (a Tokio-native, fault-tolerant actor runtime), and **Actix** (the oldest of the three, now a multi-crate workspace whose maintenance status you should read carefully before adopting). Below is what actually differs when you wire them into a real service.

## TL;DR

**If you are starting a new Rust service in 2026, use Kameo.** Its `#[derive(Actor)]` API is the least ceremony you can pay for supervision, backpressure, and distributed actors, and the crate is actively developed with roughly 1.2M downloads.

**If your team's mental model is Erlang/OTP — supervisors, `gen_server` callbacks, priority channels — use ractor.** It is the closest thing Rust has to OTP semantics, including a `ractor_cluster` companion crate for multi-node messaging.

**Only choose Actix if you already run it.** The actor crate is marked `passively-maintained`, its last substantive architectural work moved into a workspace split (`actix`, `actix-actor`, `actix-rt`, `actix-broker`), and most new Rust web work now uses `actix-web` — which does not require the actor model at all.

## Comparison at a Glance

| Dimension | ractor | Kameo | Actix |
|---|---|---|---|
| GitHub stars | **2,141** | 1,404 | **9,272** |
| Latest version | 0.16.6 | **0.22.2** | 0.13.6 |
| crates.io downloads | 1.54M | 1.22M | **21.3M** |
| Last push | 2026-11-06 | 2026-11-09 | 2026-11-08 |
| Maintenance signal | Active | Active | `passively-maintained` |
| Supervision | Yes, Erlang-style supervisors | Yes, spawn/restart policies | Manual (`Supervisor`) |
| Distribution | `ractor_cluster` | Built in (`register`/`lookup`) | Via `actix-broker` / external |
| Macro ergonomics | Attribute macros (`#[ractor::actor]`) | `#[derive(Actor)]` | Manual trait impls |
| Runtime | Tokio | Tokio | `actix-rt` (Tokio-based) |
| License | MIT | MIT | MIT OR Apache-2.0 |

Two numbers deserve context. Actix's 21M downloads are cumulative since 2017 and include every project that ever pulled it in transitively through the web stack — they do not indicate present-day momentum. ractor and Kameo, by contrast, are both past the million-download mark on much shorter timelines, and both shipped releases in the last two weeks.

## Which One for Which Job

| Use case | Pick | Why |
|---|---|---|
| New greenfield Rust service with supervision | **Kameo** | Least boilerplate; restart policies are first-class |
| Migrating an Erlang/OTP design to Rust | **ractor** | Same supervisor tree vocabulary and callback names |
| Multi-node actor mesh, no external broker | **ractor** + `ractor_cluster` | Purpose-built remote actor transport |
| Existing Actix codebase | **Actix** | Rewriting buys you little; API is stable |
| Background jobs with retries | **Kameo** | Panic isolation + bounded mailboxes give you retry semantics for free |
| Extreme message throughput, minimal abstraction | **ractor** | Priority channels and explicit message queues |

## ractor: OTP Semantics, Compiled

ractor's pitch is unusually honest — the README calls it "a pure-Rust actor framework, inspired from Erlang's `gen_server`, with the speed and performance of Rust." That is not marketing fluff; the callback names (`pre_start`, `post_stop`) and the supervisor design map directly onto OTP concepts, so an engineer who has written Erlang can read a ractor codebase without translation.

Install it:

```toml
[dependencies]
ractor = "0.16"
# optional: attribute macros for the declarative API
# ractor = { version = "0.16", features = ["actor-macros"] }
```

The modern API uses attribute macros over a message enum, which reads closer to a service definition than to a trait soup:

```rust
struct Counter;

enum CounterMessage {
    Add(u64),
    Read(ractor::RpcReplyPort<u64>),
}

#[ractor::actor(message = CounterMessage, state = u64)]
impl Counter {
    async fn pre_start(
        &self,
        _myself: ractor::ActorRef<CounterMessage>,
        _arguments: (),
    ) -> Result<u64, ractor::ActorProcessingErr> {
        Ok(0)
    }

    #[ractor::message(CounterMessage::Add(amount))]
    fn add(&self, amount: u64, state: &mut u64) {
        *state += amount;
    }

    #[ractor::rpc(CounterMessage::Read(reply))]
    fn read(&self, state: &u64) -> u64 {
        *state
    }
}
```

The `RpcReplyPort` variant is the detail people miss. In ractor, a request/response call is just another message variant carrying a reply port — so `call` and `cast` share one mailbox, one ordering guarantee, and one backpressure story. That is the OTP model, faithfully reproduced.

ractor also carries a genuine production credential: it underpins the overload-protection scheme in Meta's Rust Thrift implementation, presented at RustConf '24. If you need an argument for "this is not a hobby crate," that is the one.

Where ractor costs you: verbosity. Even with macros, you define a message enum, a state type, and every handler explicitly. For a 400-line service that is fine; for a small internal tool it is a lot of ceremony for a mailbox.

![ractor logo](/img/screenshots/ractor-logo.jpg "ractor actor framework logo")

## Kameo: Actors That Behave Like Tokio Tasks

Kameo was designed by someone who clearly liked actors but did not want to leave Tokio's ecosystem behind. Each actor runs as its own Tokio task, messages are typed through a `Message<T>` trait, and the derive macro does the boilerplate:

```toml
[dependencies]
kameo = "0.22"
```

```rust
use kameo::Actor;
use kameo::actor::Spawn;
use kameo::message::{Context, Message};

#[derive(Actor)]
struct Counter {
    count: i64,
}

struct Inc { amount: i64 }

impl Message<Inc> for Counter {
    type Reply = i64;

    async fn handle(&mut self, msg: Inc, _ctx: &mut Context<Self, Self::Reply>) -> Self::Reply {
        self.count += msg.amount;
        self.count
    }
}
```

Spawning and talking to it is three lines, and both directions are typed:

```rust
let actor_ref = Counter::spawn(Counter { count: 0 });
let count = actor_ref.ask(Inc { amount: 42 }).await?;
assert_eq!(count, 42);
```

Three properties make Kameo the default recommendation for new work. First, **panic isolation is structural**: an actor runs in its own task, so a panic in one does not take down the runtime, and the supervision policy decides whether to restart it. Second, **mailboxes can be bounded**, which gives you real backpressure instead of an unbounded queue that quietly eats memory until the OOM killer intervenes. Third, **distribution is in the crate**, not a companion:

```rust
actor_ref.register("my_actor").await?;
if let Some(remote) = RemoteActorRef::<MyActor>::lookup("my_actor").await? {
    let count = remote.ask(&Inc { amount: 10 }).await?;
}
```

The trade-off is maturity of ecosystem: Kameo at 0.22 is pre-1.0, so semver-minor releases can and do change handler signatures. Pin the exact minor version in `Cargo.toml` and read the changelog before bumping. That is a 10-minute habit that has saved more than one migration.

![Kameo actor framework banner](/img/screenshots/kameo-banner.jpg "Kameo — fault-tolerant async actors built on Tokio")

## Actix: Load-Bearing, but No Longer Load-Bearing *for You*

Actix is the framework with the most stars and the most historical gravity — and the one where you should read the metadata before the README. Its `Cargo.toml` declares `maintenance.status = "passively-maintained"`, and the repository has been split into separate crates (`actix`, `actix-actor`, `actix-rt`, `actix-broker`, `actix-derive`). That is a signal about future investment, not a verdict on code quality.

The actor API itself is stable and, once written, quite readable:

```rust
use actix::prelude::*;

struct Ping(usize);

impl Message for Ping {
    type Result = usize;
}

struct MyActor {
    count: usize,
}

impl Actor for MyActor {
    type Context = Context<Self>;
}

impl Handler<Ping> for MyActor {
    type Result = usize;

    fn handle(&mut self, msg: Ping, _: &mut Context<Self>) -> Self::Result {
        self.count += msg.0;
        self.count
    }
}

#[actix::main]
async fn main() {
    let addr = MyActor { count: 10 }.start();
    let res = addr.send(Ping(10)).await;
    println!("RESULT: {}", res.unwrap() == 20);
}
```

Notice the ergonomic tax: `Message` and `Handler` are separate trait implementations, and message types are usually structs rather than enum variants, so a multi-message actor becomes a pile of nearly identical `impl` blocks. Actor lifecycle management beyond simple restarts lives in the `Supervisor` type, which is functional but noticeably less expressive than ractor's supervisor trees.

The honest framing for 2026: **Actix's actor crate is legacy-stable, while `actix-web` remains a strong web framework that does not require actors at all.** If you inherited an Actix actor service, keep it — a rewrite buys negligible performance and a lot of risk. If you are choosing today, the maintenance signal points elsewhere. For a broader look at how `actix-web` stacks up against `axum` and `rocket` in the web layer specifically, our [Rust web framework comparison](../2026-07-13-rust-web-frameworks-actix-web-rocket-axum/) covers that decision separately.

## Traps That Only Show Up in Production

**1. Unbounded mailboxes turn a slow actor into an OOM.** Mailbox limits are not a nice-to-have. Both Kameo and ractor let you bound the queue; Actix's default `Context` mailbox is unbounded unless you configure it. An actor that processes 2k msg/s while a producer pushes 20k msg/s will happily buffer gigabytes before anything looks wrong.

**2. Supervision without backoff becomes a crash loop.** A restarted actor that immediately re-reads the same poisoned message fails again. Attach a backoff policy (Kameo exposes restart policies; ractor supervisors let you cap restart intensity) and make handlers idempotent so a redelivered message is harmless.

**3. `ask` inside a handler is the classic deadlock.** If actor A handles a message by awaiting `ask` on actor B, and B's handler awaits A, both mailboxes stall until timeout. Model the flow as a message chain, or use a correlation ID and a separate completion message.

**4. Panics inside `pre_start` do not behave like handler panics.** Initialization failures bypass the supervision path in several frameworks; return a `Result` from `pre_start` rather than unwrapping, or you get a silently dead actor that never registered.

**5. Bounded mailboxes push the problem upstream.** When a mailbox fills, `send` blocks or fails — and now the *producer* is the bottleneck. Decide explicitly between "drop oldest," "fail fast," and "block," and instrument the rejection count. That metric is the earliest signal of a capacity problem, and neither framework gives it to you for free.

**6. Distributed actors need idempotency, not just transport.** `ractor_cluster` and Kameo's remote refs move messages across nodes, but neither gives you exactly-once delivery. Any cross-node handler that touches a database needs a dedupe key, or your retry logic becomes a duplicate-write generator.

If you are layering actors into a larger async design, our comparison of [actor model frameworks across Orleans, Akka.NET, and Proto.Actor](../2026-06-20-actor-model-frameworks-orleans-akkanet-protoactor-caf/) shows how the .NET and JVM ecosystems solve the same supervision problems — useful if you are porting a design rather than starting from zero. And if your actors exist mainly to schedule recurring work, the [Rust task scheduling libraries guide](../2026-09-17-rust-task-scheduling-libraries-tokio-cron-scheduler-delay-timer-clokwerk/) covers `tokio-cron-scheduler`, `clokwerk`, and the simpler cron-in-a-task patterns that need no actor runtime at all.

## Operational Considerations Before You Commit

Actor frameworks trade one problem for another: you stop fighting shared-state concurrency and start operating supervision trees. Two operational habits pay off immediately.

**Instrument mailbox depth, not just throughput.** Every framework in this comparison exposes a reference or context handle from which you can sample queue length. A mailbox sitting above zero for sustained periods means the actor is undersized; a mailbox oscillating between empty and full means your producer is bursty and you need a buffer, not a faster handler.

**Decide the failure domain before the framework.** Ask what must survive a panic: a single actor, one actor subtree, or the whole process. Actix and ractor both let you express subtree isolation; Kameo's policies make the per-actor case the default. Frameworks support all three, but the default shapes what your team writes under deadline pressure — which is the only time it matters.

**Budget for the pre-1.0 tax.** ractor (0.16) and Kameo (0.22) are both pre-1.0. Pin minor versions, read changelogs, and keep actor code in a module with a narrow public surface. Actix at 0.13 is post-decade-stability, which is a genuine advantage if you value API freeze over ergonomics.

## FAQ

### Is an actor framework actually necessary in Rust, or is `tokio::spawn` enough?

For stateless parallel tasks, `tokio::spawn` plus a channel is simpler and faster to write. You need an actor framework when you require three things together: encapsulated mutable state that only one task can touch, supervision with restart semantics, and backpressure via bounded mailboxes. Building all three by hand is doable — roughly 300 lines of supervisor and channel plumbing — and is exactly the code these crates already test for you.

### Which framework has the best performance?

Message dispatch overhead differs by tens of nanoseconds, which is irrelevant next to almost any real handler body (a database call, a crypto operation, a JSON decode). Benchmark your own workload rather than adopting a crate on microbenchmark numbers. The performance question that actually matters is mailbox behavior under saturation, so measure rejection and queue depth, not raw dispatch speed.

### Can I mix actors with a normal async web framework?

Yes, and it is the most common architecture. Kameo actors sit comfortably behind `axum` handlers (spawn an actor at startup, hold an `ActorRef` in application state, `ask` it from handlers). ractor works the same way with `ActorRef` handles. Actix's ecosystem makes this easiest inside `actix-web`, but nothing prevents using its actor crate alongside a different web layer.

### Is Actix dying?

"Passively-maintained" is the maintainers' own label, and it is accurate: the code is stable and receives fixes, but it is not where new feature work goes. `actix-web` — a separate project with active releases — remains a strong choice for the web layer. Treat the actor crate as a stable dependency for existing services, not as the foundation for a new one.

### Do these frameworks work without Tokio?

ractor and Kameo both assume Tokio. Actix uses `actix-rt`, which is built on Tokio's runtime but schedules actors in its own arbiter threads. If you are committed to `async-std` or `smol`, none of these is a clean fit, and you are better off with a channel-based design than fighting the runtime assumption.

### How do I migrate from Actix actors to Kameo or ractor?

The mechanical part is straightforward: each `impl Message for X` becomes a Kameo `Message<X>` implementation, `Addr::send` becomes `actor_ref.ask`, and the `Supervisor` becomes a restart policy. The hard part is finding every place where a handler implicitly depended on the Actix arbiter's single-threaded execution — those assumptions surface as data races once handlers run as independent Tokio tasks. Migrate one actor subtree at a time behind a facade, not in a single branch.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Actor Frameworks in 2026: ractor vs Kameo vs Actix Compared",
  "description": "A hands-on comparison of ractor, Kameo, and Actix for building actor-based Rust services in 2026 with real code and production pitfalls.",
  "datePublished": "2026-11-14",
  "dateModified": "2026-11-14",
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
