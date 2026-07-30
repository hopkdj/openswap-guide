---
title: "Rust Benchmarking Libraries: Criterion.rs vs Iai vs Divan for Accurate Performance Measurement"
date: "2026-07-31"
tags: ["rust", "benchmarking", "performance", "criterion", "iai", "divan", "cargo", "developer-tools", "profiling", "optimization"]
draft: false
---

## Introduction

Performance is Rust's raison d'être. The language promises zero-cost abstractions and fearless concurrency, but delivering on that promise requires rigorous measurement. Writing performant code without benchmarks is like navigating without a compass — you might arrive somewhere, but you won't know if you took the optimal path.

Rust's benchmarking ecosystem has matured significantly. The classic statistical benchmark harness **Criterion.rs** (5,510 ⭐) has been joined by newer approaches: **Iai** (654 ⭐) for instruction-count-based measurement, and **Divan** (1,432 ⭐) for attribute-driven simplicity. Each takes a fundamentally different approach to answering the same question: "Is my code faster?"

This article compares these three benchmarking libraries, showing when to choose statistical measurement, instruction counting, or minimal-overhead attribute macros for your Rust performance work.

## Library Comparison

| Feature | Criterion.rs | Iai (Iai-Callgrind) | Divan |
|---------|--------------|---------------------|-------|
| Stars | 5,510 | 654 | 1,432 |
| Measurement | Statistical (wall-clock) | Instruction counts (Valgrind) | Statistical (wall-clock) |
| Noise Resilience | Excellent (p-value, confidence) | Deterministic (CPU instructions) | Good (basic statistics) |
| Setup Overhead | Moderate (groups, config) | High (Valgrind dependency) | Low (attribute macros) |
| CI Integration | `cargo-criterion` | Machine-dependent | `#[divan::bench]` |
| Async Support | Via Tokio runtime | Indirect | Native `async` support |
| Learning Curve | Moderate | Steep (requires Valgrind) | Minimal |
| Parameterized Benchmarks | Yes (`benchmark_group!`) | Limited | Yes (`#[divan::bench(args = ...)]`) |

## Criterion.rs: The Statistical Workhorse

Criterion.rs is the most widely used Rust benchmarking library. It runs your benchmark repeatedly, collecting wall-clock time measurements, and performs statistical analysis to produce confidence intervals and detect regressions:

```rust
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

fn bench_fibonacci(c: &mut Criterion) {
    c.bench_function("fib 20", |b| b.iter(|| fibonacci(black_box(20))));
}

criterion_group!(benches, bench_fibonacci);
criterion_main!(benches);
```

Criterion.rs produces HTML reports showing change over time, making it easy to spot regressions:

```rust
fn bench_sorting(c: &mut Criterion) {
    let mut group = c.benchmark_group("sorting");
    for size in [100, 1000, 10_000].iter() {
        group.bench_with_input(
            BenchmarkId::new("quicksort", size),
            size,
            |b, &size| {
                let mut data: Vec<i32> = (0..size).rev().collect();
                b.iter(|| {
                    data.sort_unstable();
                    black_box(&data);
                })
            },
        );
    }
    group.finish();
}
```

**Key advantages:** Statistical rigor catches measurement noise; HTML reports for trend tracking; de facto standard in the Rust ecosystem; excellent documentation and community support.

## Iai: Instruction-Level Precision

Iai (and its successor `iai-callgrind`) takes a completely different approach. Instead of measuring wall-clock time, it uses Valgrind's Callgrind tool to count CPU instructions executed. This provides deterministic, machine-independent measurements:

```rust
use iai_callgrind::{library_benchmark, library_benchmark_group, main};
use std::hint::black_box;

fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

#[library_benchmark]
#[bench::small(10)]
#[bench::medium(20)]
#[bench::large(30)]
fn bench_fibonacci(n: u64) -> u64 {
    fibonacci(black_box(n))
}

library_benchmark_group!(
    name = my_group;
    benchmarks = bench_fibonacci
);

main!(library_benchmark_groups = my_group);
```

Instruction counting eliminates measurement noise entirely — the same code on the same input always produces the same count. This is invaluable for micro-optimizations where wall-clock variance would drown out small improvements:

```rust
#[library_benchmark]
#[bench::vec(1000)]
#[bench::vec(10000)]
fn bench_hashmap_lookup(size: usize) -> Option<i32> {
    let map: HashMap<i32, i32> = (0..size as i32).map(|i| (i, i * 2)).collect();
    black_box(map.get(&black_box(size as i32 / 2))).copied()
}
```

**Key advantages:** Deterministic results (no CI noise); catches sub-instruction-level changes; machine-independent comparisons; ideal for micro-benchmarking hot paths.

## Divan: Attribute-Driven Simplicity

Divan is the newest contender, designed for ergonomics. Instead of macro-heavy setup, you annotate functions with `#[divan::bench]`:

```rust
use divan::black_box;

fn fibonacci(n: u64) -> u64 {
    match n {
        0 => 0,
        1 => 1,
        _ => fibonacci(n - 1) + fibonacci(n - 2),
    }
}

#[divan::bench]
fn fib_10() -> u64 {
    fibonacci(black_box(10))
}

#[divan::bench]
fn fib_20() -> u64 {
    fibonacci(black_box(20))
}

fn main() {
    divan::main();
}
```

Divan supports parameterized benchmarks with minimal ceremony:

```rust
#[divan::bench(args = [100, 1000, 10000])]
fn vector_sort(n: usize) -> Vec<i32> {
    let mut data: Vec<i32> = (0..n).rev().collect();
    data.sort_unstable();
    data
}

#[divan::bench(args = [16, 256, 4096])]
fn base64_encode(n: usize) -> String {
    use base64::{Engine as _, engine::general_purpose};
    let data = vec![0u8; n];
    general_purpose::STANDARD.encode(&data)
}
```

Async benchmarks are a Divan strength — just add `#[divan::bench]` to async functions:

```rust
#[divan::bench]
async fn async_request() -> reqwest::Result<()> {
    let client = reqwest::Client::new();
    let _ = client.get("http://localhost:8080/health").send().await?;
    Ok(())
}

#[divan::bench(threads = [1, 2, 4, 8])]
#[tokio::test]
async fn concurrent_processing(threads: usize) {
    // Benchmark multi-threaded async workloads
}
```

## Choosing the Right Tool

| Scenario | Recommended Library | Why |
|----------|-------------------|-----|
| CI regression detection | Divan | Simple setup, good-enough stats, fast |
| Micro-optimization of hot loops | Iai | Deterministic instruction counts |
| Research/paper-quality benchmarks | Criterion.rs | Statistical rigor, published methods |
| Async code benchmarking | Divan | Native async support |
| Large project with benchmark history | Criterion.rs | HTML reports, trend tracking |
| Quick ad-hoc measurement | Divan | Minimal boilerplate |

## Why Self-Host Your Rust Benchmarking Pipeline?

Performance work without automated benchmarks is guesswork. When you integrate benchmarks into CI:

- **Prevent performance regressions** — every PR runs benchmarks, catching slowdowns before they merge. See our [Rust error handling guide](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/) for patterns that maintain performance while improving ergonomics.

- **Guide optimization efforts** — benchmark results tell you exactly which functions dominate runtime. Combined with profiling tools, you can focus optimization where it matters. Our [Rust database libraries comparison](../2026-06-23-rust-database-libraries-diesel-seaorm-rusqlite/) shows how benchmark-informed choices lead to better ORM performance.

- **Document performance characteristics** — public benchmarks serve as living documentation of your library's performance envelope. For more on Rust library selection, see our [Rust URL parsing guide](../2026-06-21-url-parsing-libraries-ada-uriparser-llhttp-rust-url/).


When combined, these three approaches — statistical benchmarking with Criterion.rs for confidence, instruction counting with Iai for precision, and Divan for rapid development — form a complete performance measurement toolkit that catches regressions at every level of the optimization stack.
## Benchmarking in Production: Profiling-Guided Optimization

Benchmarking libraries answer "is it faster?" but profiling answers "what should I optimize?" A mature Rust performance workflow combines both:

**Flamegraph Integration**: Criterion.rs benchmarks can be profiled with `perf` or `cargo-flamegraph` to identify which functions consume the most cycles. Run your benchmark binary with profiling enabled, then visualize the results:

```bash
cargo flamegraph --bench my_benchmark -- --profile-time 10
```

**Comparative Regression Detection**: Store historical benchmark results in your repository and compare PRs against them. Criterion.rs supports baseline comparison natively:

```rust
// Save baseline
c.bench_function("parse", |b| b.iter(|| parse(black_box(input))));

// Later, compare against saved baseline
criterion::compare::against_baseline("parse", saved_results);
```

**Cache-Aware Micro-Benchmarking**: For data structure benchmarks where cache behavior dominates, use `iai-callgrind` to get cache-miss counts alongside instruction counts. This reveals whether a "faster" algorithm is actually slower due to cache thrashing on real hardware:

```rust
#[library_benchmark]
#[bench::small(100)]
#[bench::large(100000)]
fn bench_cache_sensitive(size: usize) -> u32 {
    let data: Vec<u32> = (0..size).collect();
    // Iai-callgrind will report both instruction count AND cache misses
    process_in_chunks(&data, 64)
}
```

**Continuous Benchmarking with Bencher**: For teams that need automated performance tracking, tools like Bencher integrate with all three Rust benchmarking libraries to track performance over time in CI, sending alerts when a PR regresses beyond a configured threshold. This closes the loop from local benchmarking to team-wide performance guarantees.



## FAQ

### Does Criterion.rs work with async code?

Criterion.rs can benchmark async code using Tokio's `block_on` in the benchmark closure. However, Divan provides native async support that's more ergonomic for complex async workloads. For Iai, async support is indirect since instruction counting is inherently synchronous.

### How do I run benchmarks in CI?

All three libraries support CI execution. Divan requires `cargo test --bench` with feature flags. Criterion.rs uses `cargo bench` or `cargo-criterion` for machine-readable output. Iai requires Valgrind installed on CI runners (available for Linux, harder on macOS CI).

### Why use instruction counting instead of wall-clock time?

Wall-clock time is affected by CPU frequency scaling, other processes, cache warmth, and OS scheduling. Instruction counting gives deterministic results — the same code always counts the same number of instructions. This is ideal for comparing algorithmic optimizations but doesn't account for cache effects or I/O.

### Can I combine multiple benchmarking approaches?

Yes — many projects use Criterion.rs for macro-benchmarks and Iai for micro-benchmarks of critical hot paths. Divan can serve as the primary benchmark harness with Criterion.rs used for published performance numbers requiring statistical confidence intervals.

### How do I handle benchmark setup/teardown costs?

Criterion.rs provides `benchmark_group` with `throughput` and `sample_size` controls. Iai's library benchmarks allow setup functions via `#[library_benchmark(setup = my_setup)]`. Divan supports `#[divan::bench(setup = ...)]` for per-iteration setup. Ensure setup cost isn't counted in the measurement by using the library's built-in mechanisms rather than inlining setup code.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Benchmarking Libraries: Criterion.rs vs Iai vs Divan for Accurate Performance Measurement",
  "description": "Compare Criterion.rs, Iai, and Divan for Rust benchmarking. Learn when to use statistical measurement, instruction counting, or attribute-driven benchmarks for performance optimization.",
  "datePublished": "2026-07-31",
  "dateModified": "2026-07-31",
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
