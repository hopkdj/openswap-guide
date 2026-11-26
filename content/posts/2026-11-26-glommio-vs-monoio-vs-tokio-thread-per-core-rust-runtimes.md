---
title: "Glommio vs Monoio vs Tokio in 2026: Thread-per-Core Rust Runtimes Compared"
date: "2026-11-26"
tags: ["rust", "async", "performance", "io-uring", "developer-tools"]
draft: false
---

Your Rust service handles 40,000 requests per second and still shows p99 latency spikes that no amount of profiling explains. The metrics look clean, the CPU is at 60%, and yet every few seconds one request waits 80 ms. That spike is usually the work-stealing scheduler moving a task to a core whose L1/L2 cache no longer holds its data — and it is the entire reason thread-per-core runtimes exist.

**Tokio** runs a work-stealing scheduler across a thread pool. **Glommio** and **Monoio** pin one executor per CPU core and never move a task, relying on `io_uring` for I/O. The difference is not academic: for sharded, cache-sensitive workloads the thread-per-core model can cut p99 latency dramatically, while for general-purpose services it will quietly ruin your throughput.

## TL;DR — Quick Verdict

- **Building a normal web service, gRPC server, or anything using the Tokio ecosystem** → **Tokio**. Its 33,805 stars reflect ecosystem gravity, not just quality: `hyper`, `tonic`, `sqlx`, and `tracing` all assume it.
- **Building a sharded, IO-heavy service where p99 matters more than average** → **Glommio**. Cooperative scheduling, no helper threads, `DmaFile` for direct-storage I/O, and a design that assumes you own the machine.
- **You want the `io_uring` performance model but need a smaller, more actively released codebase with owned buffers** → **Monoio**. ByteDance's runtime, 5,138 stars, released as recently as October 2026.

The honest summary: **Tokio is the default, Glommio is the specialist, and Monoio is the pragmatic middle**. If you cannot name the shard key of your workload, you do not need thread-per-core.

## Runtime Comparison (data pulled 2026-11-26)

| Dimension | Tokio | Glommio | Monoio |
|---|---|---|---|
| **GitHub stars** | 33,805 | 3,676 | 5,138 |
| **Last commit** | 2026-11-24 | 2026-08-31 | 2026-10-16 |
| **Latest version** | 1.4x line | 0.9.0 | 0.2.4 |
| **Scheduling model** | Work-stealing, multi-threaded | Cooperative, thread-per-core | Thread-per-core |
| **I/O backend** | epoll (mio) | `io_uring` only | `io_uring` only |
| **Requires Linux** | No (BSD, macOS, Windows) | Yes (kernel ≥ 5.8) | Yes |
| **Task must be `Send`** | Yes for `tokio::spawn` | No (`spawn_local`) | No |
| **Buffer model** | Borrowed (`AsyncRead`) | Borrowed | Owned/rented (`AsyncReadRent`) |
| **MSRV** | 1.70+ | 1.70 | 1.75+ |
| **Ecosystem compatibility** | Native | Limited (`hyper` via compat layers) | `monoio-compat` for `hyper`/`tonic` |
| **Debugging tooling** | `tokio-console`, rich tracing | Basic | Basic |
| **Best fit** | General async services | Cache-sensitive sharded services | io_uring services with owned buffers |

Star counts are a proxy for ecosystem, not for performance. Note that Glommio's last release activity trails the other two by roughly three months, and its 0.x version number is an honest signal about API stability.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Recommended runtime | Why |
|---|---|---|
| REST or gRPC API with a standard framework | **Tokio** | Everything integrates with it; no compat layer needed |
| Database proxy or message broker with per-connection state | **Glommio** | Pinning a connection to a core keeps its buffers hot |
| Multi-tenant SaaS with unpredictable load | **Tokio** | Work stealing absorbs skew that would starve a shard |
| Storage engine, log shipper, or file server | **Glommio** | `DmaFile` bypasses the page cache deliberately |
| You need `io_uring` but dislike `!Send` ergonomics | **Monoio** | Owned buffers make callbacks and cross-task passing easier |
| Running inside containers with default seccomp | **Tokio** | Docker's default profile blocks `io_uring` syscalls |
| Pet project that must also run on macOS | **Tokio** | The other two are Linux-only |

## Tokio — The Baseline You Are Probably Already Using

Tokio's model is a work-stealing scheduler: tasks land in per-worker queues, and idle workers steal from busy ones. That design is why a Tokio service survives one slow database query without stalling a core, and why a monolithic `#[tokio::main]` binary can saturate a 64-core machine with no tuning.

```rust
use tokio::net::TcpListener;

#[tokio::main]
async fn main() -> std::io::Result<()> {
    let listener = TcpListener::bind("0.0.0.0:8080").await?;

    loop {
        let (mut socket, _addr) = listener.accept().await?;
        // Tasks must be Send: they may resume on any worker thread
        tokio::spawn(async move {
            let (mut reader, mut writer) = socket.split();
            let _ = tokio::io::copy(&mut reader, &mut writer).await;
        });
    }
}
```

The cost of that flexibility is exactly the latency spike described above: a task can resume on a different core, dragging its hot data through another cache. For most workloads — HTTP with JSON serialization, a few database round trips — this is noise. For a 100-byte request that does one hash lookup, it is the dominant cost.

**When Tokio is the wrong answer:** when your workload is strictly partitioned (per-connection, per-shard, per-tenant) and you want deterministic core placement. Tokio will happily migrate your pinned-connection state around, and its `LocalSet` escape hatch gets you pinning without the `io_uring` I/O model.

## Glommio — Cooperative Thread-per-Core, Datadog Style

Glommio removes two things most async code assumes: helper threads and work stealing. Each executor is pinned to a core with `Placement::Fixed`, tasks are `!Send`, and everything runs cooperatively — meaning a blocking call stalls that core's entire shard. That constraint is the feature.

```rust
use glommio::prelude::*;

fn main() {
    // One executor, pinned to CPU 0 — tasks never migrate
    LocalExecutorBuilder::new(Placement::Fixed(0))
        .spawn(|| async move {
            let listener = glommio::net::TcpListener::bind("0.0.0.0:8080").unwrap();
            loop {
                let stream = listener.accept().await.unwrap().0;
                glommio::spawn_local(async move {
                    // Handle the connection on this core, always
                    let _ = handle(stream).await;
                })
                .detach();
            }
        })
        .expect("failed to spawn local executor")
        .join();
}
```

Two hard requirements bite people on day one. The kernel must be **5.8 or newer** with `io_uring` enabled, and the process needs locked memory — at least **512 KiB per executor**, more when you spawn several:

```bash
# /etc/security/limits.conf
*    hard    memlock        512
*    soft    memlock        512

# verify after re-login
ulimit -l    # 512
```

Glommio also ships `DmaFile`, which performs direct-memory-access reads and writes that deliberately bypass the page cache. For a log-structured store or an object-storage gateway that already manages its own cache, this removes a double-buffering cost that epoll-based runtimes cannot avoid.

**Where Glommio hurts:** any blocking operation — `std::fs`, a synchronous DNS resolver, a mutex held across an await — freezes that shard. There is no work stealing to rescue you, so one misbehaving tenant means one core at 100% and everyone on it waiting. You also inherit a thinner ecosystem: `hyper` needs a compatibility layer, and `tokio-console` does not apply.

## Monoio — io_uring With Owned Buffers

Monoio takes the same thread-per-core stance but fixes the ergonomic problem that makes Glommio awkward: buffer ownership. Its traits are `AsyncReadRent` and `AsyncWriteRent`, and reads hand you back the buffer, which makes the borrow checker stop fighting your connection pool.

```rust
use monoio::io::{AsyncReadRent, AsyncWriteRentExt};
use monoio::net::{TcpListener, TcpStream};

#[monoio::main]
async fn main() {
    let listener = TcpListener::bind("127.0.0.1:50002").unwrap();
    println!("listening");

    loop {
        let incoming = listener.accept().await;
        match incoming {
            Ok((stream, addr)) => {
                println!("accepted a connection from {}", addr);
                monoio::spawn(echo(stream));
            }
            Err(e) => {
                println!("accepted connection failed: {}", e);
                return;
            }
        }
    }
}

async fn echo(stream: TcpStream) -> std::io::Result<()> {
    let mut buf = Vec::with_capacity(4096);
    loop {
        let (res, buf_back) = stream.read(buf).await;
        buf = buf_back;
        if res? == 0 {
            return Ok(());
        }
        let (res, buf_back) = stream.write_all(buf).await;
        buf = buf_back;
        res?;
    }
}
```

The rented-buffer pattern looks verbose in a minimal example, but in real code it eliminates the `poll_read` + `unsafe` buffer juggling that every hand-written `io_uring` server ends up doing. Monoio's release cadence also looks healthier than Glommio's at the moment: 0.2.4 landed in October 2026.

**Where Monoio hurts:** it is version 0.2, its documentation still assumes you read the source, and the compat layer for `hyper` works but adds a translation cost. Timers exist but the ecosystem around observability is thin compared with Tokio's.

## The Traps Nobody Mentions in Benchmarks

Four things decide whether thread-per-core works for you, and none of them appear in the marketing:

1. **`io_uring` is blocked by default in Docker and many Kubernetes runtimes.** The default seccomp profile denies `io_uring_setup`, so a Glommio or Monoio binary crashes at executor start inside a stock container while working fine on the host. You need `--security-opt seccomp=unconfined` or a custom profile that allows the `io_uring_*` syscalls. Verify before you benchmark anything.
2. **Skew is fatal, not annoying.** With work stealing, one hot shard borrows idle cores. Without it, one hot shard means one core at 100% and 63 idle. If your key distribution is not uniform — and it never is — add a shard-splitting strategy before you migrate.
3. **Blocking calls break correctness, not just speed.** A `std::fs::read` inside a pinned executor blocks every task on that core indefinitely. Audit for sync I/O, blocking DNS (`getaddrinfo`), and `std::sync::Mutex` held across `.await`.
4. **Benchmarks overstate the gain when the kernel is old.** `io_uring` behaviour changed significantly across the 5.8–6.6 range. If your fleet runs an older LTS kernel, measure there — not on your 6.14 workstation.

If you are tuning a Rust data path rather than a network path, our [Rust embedded key-value engine comparison](../2026-09-18-rust-embedded-key-value-engines-sled-redb-fjall/) covers storage engines that sit naturally behind a thread-per-core runtime, and the [Rust JSON library benchmarks](../2026-10-03-rust-json-libraries-serde-json-simd-json-sonic-rs/) matter more than runtime choice once serialization dominates the profile. For teams still building the application layer, the [Rust TUI framework comparison](../2026-08-26-rust-tui-frameworks-ratatui-cursive-crossterm-comparison/) is a good reminder that most Rust workloads are nowhere near I/O-bound.

## FAQ

### Is thread-per-core actually faster than Tokio?

It depends entirely on the workload shape. For sharded services with small per-request CPU footprints and high request rates, thread-per-core avoids task migration and cache invalidation, which usually improves p99 latency. For workloads with skewed load, blocking calls, or heavy per-request compute, Tokio's work stealing wins because it can redistribute work at runtime. Always benchmark your own service: published numbers rarely transfer.

### Can I use Glommio or Monoio with hyper and tonic?

Only through compatibility layers. Monoio ships `monoio-compat`, which adapts `hyper` and `tonic` to its runtime; Glommio relies on community compat crates with less complete coverage. Expect to lose some features and to debug trait mismatches. If you depend heavily on the Tokio ecosystem, Tokio is the pragmatic choice.

### Why does my Glommio binary fail inside Docker?

The default Docker seccomp profile blocks `io_uring_setup` and related syscalls, so the executor cannot initialize. You will see an error at runtime, not at compile time. Run with `--security-opt seccomp=unconfined` for testing, or write a custom seccomp profile that permits `io_uring_setup`, `io_uring_enter`, and `io_uring_register`.

### What is the minimum kernel version for these runtimes?

Glommio documents a minimum of Linux 5.8 for `io_uring` discovery probes; Monoio targets similar kernels. In practice, use 6.1 or newer for production: earlier kernels have `io_uring` behaviours that were later fixed, and some container runtimes refuse the syscalls outright. Both runtimes are Linux-only — there is no macOS or Windows path.

### Do I need to raise `memlock` limits?

Yes for Glommio, which needs at least 512 KiB of locked memory per executor, and more when spawning multiple executors. Set `memlock` in `/etc/security/limits.conf` and re-login for it to apply. Monoio has similar requirements because `io_uring` rings are locked memory. In containers, remember that `ulimit -l` inside the container may differ from the host.

### Which runtime should a startup standardise on?

Tokio, unless you have a measured latency problem that only thread-per-core solves. The hiring, tooling, and library ecosystem around Tokio is worth more than a few percent of p99 for most teams. Revisit once your service is CPU-bound, sharded, and you can point at a specific cache-migration cost in a profile.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Glommio vs Monoio vs Tokio in 2026: Thread-per-Core Rust Runtimes Compared",
  "description": "A practical comparison of Rust async runtimes: Tokio's work-stealing scheduler versus Glommio and Monoio thread-per-core io_uring designs, with real code, kernel requirements, and production pitfalls.",
  "datePublished": "2026-11-26",
  "dateModified": "2026-11-26",
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
