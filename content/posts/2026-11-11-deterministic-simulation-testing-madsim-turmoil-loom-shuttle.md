---
title: "Simulation Testing in 2026: madsim vs turmoil vs loom vs shuttle"
date: "2026-11-11"
tags: ["testing", "rust", "concurrency", "distributed-systems", "developer-tools"]
draft: false
description: "Deterministic simulation and concurrency permutation testing compared: madsim, turmoil, loom and shuttle, with real code, real star counts and the limits nobody mentions."
---

# Simulation Testing in 2026: madsim vs turmoil vs loom vs shuttle

A test suite that passes 10,000 times in CI tells you almost nothing about a distributed system. The bugs that take down production — a replica that loses an acknowledged write during a partition, a retry storm that finishes out of order, a lock that is *usually* acquired first — need a specific interleaving, a specific packet drop, and a clock that jumps at the wrong moment. Waiting for the RNG of real life to produce them is not a strategy.

**Deterministic simulation testing** flips the problem: instead of running your code against real time and real networks and hoping, you run it against a simulated network, a simulated clock and a seeded RNG, then replay any failing seed until the bug is fixed. FoundationDB is the famous proof that this works. The tooling is now open source and usable in an afternoon.

This is a practical comparison of the four projects worth your time in 2026, and — just as important — which of them solves which class of bug.

## TL;DR / Quick Verdict

- **Distributed systems in Rust (multi-node, network faults):** `turmoil` (1,298★, pushed 2026-11-08) if you want intentional control; `madsim` (1,187★) if you want a drop-in runtime that simulates an entire cluster, including S3 and Kafka clients.
- **Concurrent data structures, atomics, lock-free queues:** `loom` (2,867★, pushed 2026-11-08). It is the only tool here that permutes *memory orderings*, and it is the reason several tokio internals ship at all.
- **Same class of bug, less state explosion:** `shuttle` (1,114★, pushed 2026-11-05) uses randomized scheduling with probabilistic guarantees instead of exhaustive permutation — faster, but not a proof.
- **Do not** use any of these as a substitute for real-network chaos testing. Simulation finds logic bugs; it does not reproduce kernel, MTU or cloud-provider behavior.

## The four approaches, side by side

| Project | Model | What it controls | Failure classes it finds | Stars | Last push | Cost per run |
|---|---|---|---|---|---|---|
| turmoil | Single-threaded multi-host simulation | Simulated network + filesystem, seeded RNG, manual `elapse` | Partitions, drops, ordering, timeouts, restart storms | 1,298 | 2026-11-08 | Milliseconds |
| madsim | Drop-in `tokio` replacement runtime | Network, clock, randomness, S3/Kafka/etcd clients | Cross-node consistency, lease expiry, retry duplication | 1,187 | 2026-02-16 | Seconds |
| loom | Exhaustive schedule permutation | Thread interleavings + C11 memory model | Data races, lost updates, ABA, missing fences | 2,867 | 2026-11-08 | Seconds to minutes |
| shuttle | Randomized schedule exploration | Interleavings, with bounded iterations | Races in code where exhaustive search explodes | 1,114 | 2026-11-05 | Seconds |

The distinction that matters: **turmoil and madsim test your system, loom and shuttle test your code.** If the bug requires two nodes disagreeing about the order of writes, reach for the first pair. If the bug requires two threads disagreeing about a shared `AtomicUsize`, reach for the second.

## Decision matrix

| Your situation | Use | Why |
|---|---|---|
| Rust service with 3+ nodes and a replication protocol | turmoil | You script the exact partition, latency and crash sequence |
| You already use tokio + tonic + rdkafka and want minimal refactor | madsim | `package = "madsim-tokio"` swap plus `--cfg madsim` |
| Writing a lock-free queue, ring buffer or custom `Arc` | loom | Exhaustive permutation is the only thing that finds the rare fence bug |
| Loom run never finishes because the state space explodes | shuttle | Randomized exploration with configurable iterations |
| Testing retry/backoff correctness across a partition | turmoil | `elapse` advances simulated time instantly; no real sleeping |
| Testing that a lease actually expires | madsim or turmoil | Both control the clock; `sleep(1h)` costs zero real time |
| Validating behavior under real kernel/cloud faults | none of these | Use fault injection proxies instead — see our [chaos testing comparison](../2026-04-20-toxiproxy-vs-pumba-vs-chaosmonkey-self-hosted-fault-injection-chaos-testing-guide-2026/) |

## turmoil: scripted hardship, zero real waiting

Turmoil runs every host inside one thread against a simulated network. Nothing is real: not the sockets, not the filesystem, not the clock. That is why a test that simulates a five-minute outage finishes in milliseconds.

```rust
use std::time::Duration;
use turmoil::Builder;

#[test]
fn writer_survives_leader_partition() -> turmoil::Result {
    let mut sim = Builder::new().build();

    sim.host("primary", || async {
        serve_writes().await;
    });
    sim.host("replica", || async {
        follow_primary().await;
    });

    sim.client("fault-injector", async {
        sim::partition("primary", "replica");
        sim::elapse(Duration::from_secs(30));
        sim::repair("primary", "replica");
        sim::elapse(Duration::from_secs(30));
        Ok(())
    });

    sim.run()
}
```

```toml
[dev-dependencies]
turmoil = "0.7"
```

The family split matters when you adopt it: `turmoil` is the full harness, while `turmoil-net` and `turmoil-fs` are drop-in replacements for `tokio::net` and `std::fs`/`tokio::fs`. That means you can simulate the network *without* simulating the filesystem, which is often what you want — a simulated filesystem hides the fsync and directory-durability bugs you were trying to catch. The crate is mid-refactor (network and filesystem being lifted into separate crates), so pin the version and expect API movement.

**Where it hurts:** you write the fault script yourself. Coverage is exactly as good as your imagination, and the simulated network does not model TCP segmentation, MTU limits or kernel buffer pressure.

## madsim: replace tokio, simulate the cluster

madsim takes the opposite bet. Instead of giving you fault-injection primitives, it gives you a *deterministic runtime* that looks like tokio, plus simulated clients for the services your code already talks to:

```toml
[dependencies]
madsim = "0.2"
tokio = { version = "0.2", package = "madsim-tokio" }
tonic = { version = "0.5", package = "madsim-tonic" }
rdkafka = { version = "0.3", package = "madsim-rdkafka" }
aws-sdk-s3 = { version = "0.5", package = "madsim-aws-sdk-s3" }
```

```bash
# Normal build: these crates behave exactly like the originals.
cargo test

# Simulation build: network, clock and randomness become deterministic.
RUSTFLAGS="--cfg madsim" cargo test
```

That `--cfg madsim` flag is the whole trick. Your production code paths are unchanged; under the flag, `tokio::time::sleep` advances virtual time, `rand` returns seeded values, and the network layer injects delays and drops according to the simulation seed. Because everything is seeded, a failure prints a seed you can replay deterministically — the difference between "flaky test" and "reproducible bug".

**Where it hurts:** the moment you add a database driver or SDK that madsim has no simulator for, you either patch it or drop simulation for that component. The patched-crates list (`quanta`, `getrandom`, `tokio-postgres`, `tokio-stream`) is a maintenance surface you inherit. Also note the last push: **2026-02-16**. It works, but it is not moving as fast as turmoil or loom.

## loom: exhaustive permutation of your concurrency

loom is a different category. It does not care about your cluster; it cares that the compiler and CPU may reorder your atomics. It runs the test body repeatedly, permuting every interleaving allowed by the C11 memory model, with state reduction to keep the explosion survivable:

```rust
use loom::sync::Arc;
use loom::sync::atomic::{AtomicUsize, Ordering};
use loom::thread;

#[test]
fn counter_increment_is_not_lost() {
    loom::model(|| {
        let counter = Arc::new(AtomicUsize::new(0));

        let writer = counter.clone();
        let handle = thread::spawn(move || {
            writer.fetch_add(1, Ordering::Relaxed);
        });

        counter.fetch_add(1, Ordering::Relaxed);
        handle.join().unwrap();

        assert_eq!(counter.load(Ordering::SeqCst), 2);
    });
}
```

```toml
[target.'cfg(loom)'.dependencies]
loom = "0.7"
```

Two practical rules. First, loom tests live behind `cfg(loom)` so your normal build does not pay for them; run them in a dedicated CI job with `RUSTFLAGS="--cfg loom" cargo test --release`. Second, keep the test body **tiny** — three threads and two atomics is roughly 10,000 permutations; add a loop and you will wait forever. When it explodes, `loom::model::Builder` lets you cap exploration (`max_branches`, `max_permutations`) so you get partial coverage instead of a hung job.

The `#[should_panic]` pattern is deliberate: you write the test asserting the *correct* invariant, watch loom find an interleaving that violates it, then fix the code until the panic disappears. That inversion — a test that fails when your code is broken, not when the environment is unlucky — is the entire value proposition.

## shuttle: randomized exploration when exhaustive is impossible

shuttle (from AWS Labs) explores schedules randomly rather than exhaustively, which trades a proof for speed and reach:

```rust
use shuttle::sync::{Arc, Mutex};

#[shuttle::test]
fn two_pushes_are_both_visible() {
    let log = Arc::new(Mutex::new(Vec::new()));

    let a = log.clone();
    let first = shuttle::thread::spawn(move || a.lock().unwrap().push(1));

    log.lock().unwrap().push(2);
    first.join().unwrap();

    assert_eq!(log.lock().unwrap().len(), 2);
}
```

By default a `#[shuttle::test]` runs the body under many randomized schedules and shrinks any failure to a shorter reproduction. For explicit control, `shuttle::check_random(f, iterations)` runs a fixed number of random schedules, while `shuttle::check_pct` uses probabilistic concurrency testing — a scheduling strategy that provably finds bugs faster than uniform random sampling on many workloads.

**Where it hurts:** randomness means "passed" is a probability statement, not a proof. A green shuttle run with 1,000 iterations is strong evidence; a green loom run over the full state space is much stronger. Use shuttle when loom cannot finish.

## What simulation testing actually catches (and what it does not)

Real classes of bug these tools have earned their reputation on:

1. **Duplicate side effects after timeout.** The client times out, retries, and the first request was actually applied. Only a simulated network that can drop the *response* reproduces this deterministically.
2. **Lease and TTL expiry races.** With a simulated clock you can put a write right at the boundary of lease expiry, every time, instead of once per hundred CI runs.
3. **Lost updates in lock-free structures.** loom's bread and butter: `Relaxed` where `Acquire`/`Release` was required, visible only on weakly ordered hardware.
4. **Restart storms.** Crash every node in sequence, then verify the system converges instead of deadlocking on a partial quorum.

What they cannot do: reproduce a real kernel's `TCP_DEFER_ACCEPT`, model a cloud provider's network partition semantics exactly, validate TLS handshakes, or catch bugs in code paths that only execute against a real database's query planner. Simulation is a complement to real-environment testing, not a replacement — and it runs in CI in seconds, so there is no excuse for skipping it.

If your Rust test infrastructure is still just `cargo test`, our [Rust testing toolchain comparison](../2026-08-25-rust-testing-cargo-test-nextest-rstest-comparison/) covers the runner layer, and the [async runtime comparison](../2026-09-03-rust-async-runtimes-tokio-async-std-smol-comparison/) explains why runtime choice changes which simulation approach is even available to you.

## FAQ

**Is deterministic simulation testing only practical for Rust?**
As open-source tooling, yes — madsim, turmoil, loom and shuttle are all Rust. The *technique* is language-agnostic (FoundationDB implemented it in C++), but outside Rust you generally build it yourself: an injectable clock, an injectable RNG, and a network abstraction you can swap. The design work is the hard part, and these crates are mostly a head start on the plumbing.

**How long does a loom test take in CI?**
A two-thread test with a handful of atomic operations completes in seconds. Three threads with a mutex and a loop commonly run into minutes, because loom explores the full interleaving space. Budget a separate CI job with a timeout, cap exploration with `loom::model::Builder`, and keep loom tests out of your main `cargo test` run.

**Do I need to rewrite my service to use madsim?**
Not the logic, but the dependency graph. You swap `tokio`, `tonic` and any supported clients for the `madsim-*` equivalents and build with `--cfg madsim`. Code that calls an unsupported client (a proprietary SDK, an unusual database driver) cannot run under simulation without a shim. Start by simulating the one subsystem you actually distrust.

**Can turmoil simulate disk failures?**
Yes — the family includes `turmoil-fs` as a drop-in for `std::fs`/`tokio::fs`, with torn writes and crash behavior. But think twice before enabling it: a simulated filesystem will not reveal `fsync` semantics or directory-entry durability, because those bugs live in the real kernel. Simulate the network, test the filesystem on a real (or `dm-flakey`) device.

**What seed do I put in CI, and how do I replay a failure?**
For madsim, the failure output includes the seed; re-run with the same seed and the execution is byte-for-byte identical. For turmoil, drive randomness from a seeded RNG you control and log the seed on failure. For loom, there is no seed — the failure is a schedule, and loom prints the interleaving it found. Store seeds as test artifacts; a bug you cannot replay is a bug you will ship twice.

**Does this replace chaos engineering in staging?**
No. Chaos engineering validates operational readiness — runbooks, alerts, failover automation — against real infrastructure. Simulation validates protocol and concurrency logic against a model. Teams that do both find different bugs at different stages, which is exactly the point.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Simulation Testing in 2026: madsim vs turmoil vs loom vs shuttle",
  "description": "Deterministic simulation and concurrency permutation testing compared: turmoil, madsim, loom and shuttle, with real code samples, GitHub star counts, decision matrix and the limits of simulation testing.",
  "datePublished": "2026-11-11",
  "dateModified": "2026-11-11",
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
