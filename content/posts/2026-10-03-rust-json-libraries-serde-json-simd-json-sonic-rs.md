---
title: "Rust JSON Libraries in 2026: serde_json vs simd-json vs sonic-rs (Real Benchmarks)"
date: "2026-10-03"
tags: ["rust", "json", "performance", "developer-tools"]
draft: false
---

Your Rust service boots fine in staging, then melts in production — and `perf` points straight at JSON deserialization. It is the same story in every API gateway, log shipper, and event pipeline: JSON parsing quietly eats 20–40% of your CPU budget, and the default choice, `serde_json`, was never designed to be the fastest parser in the room. It was designed to be the most correct and most ergonomic one. That tradeoff stops paying off the moment your throughput is measured in gigabytes per minute rather than requests per second.

This guide compares the three Rust JSON libraries that actually matter in 2026: **serde_json** (the default), **simd-json** (the SIMD-accelerated port of simdjson), and **sonic-rs** (ByteDance's newer SIMD parser). Every number below comes from the projects' own published benchmarks, and every code sample is lifted from their official READMEs.

## TL;DR — Quick Verdict

**Reach for `serde_json` by default** — it is battle-tested, dependency-light, and works with every `#[derive(Serialize, Deserialize)]` type you already have. **Switch to `simd-json`** when profiling proves JSON is your bottleneck and your payloads are large (>1 KB) and mostly UTF-8 — it keeps serde compatibility while adding SIMD scanning. **Pick `sonic-rs`** when raw deserialization throughput is the goal and you can accept a younger, smaller ecosystem: it beats `serde_json` by roughly **2.9×** on the classic `twitter.json` workload.

The honest rule: measure first. For small payloads the SIMD parsers save you very little, and their required mutable input buffers change your API surface.

## Comparison Table

| Feature | serde_json | simd-json | sonic-rs |
|---|---|---|---|
| GitHub stars | **5,642** | 1,430 | 931 |
| Last activity | 2026-08-08 | 2026-08-23 | 2026-09-11 |
| SIMD acceleration | No (scalar) | Yes (two-stage) | Yes (selective) |
| Works with `serde` derives | Yes (native) | Yes (compat module) | Yes (compat module) |
| Requires mutable input (`Vec<u8>`) | No | Yes | Yes (`from_slice_unchecked` optional) |
| Untyped `Value` type | `serde_json::Value` | `OwnedValue` / `BorrowedValue` / `Tape` | `sonic_rs::Value` |
| `no_std` / alloc-only support | Yes (`alloc` feature) | Partial | No |
| Maturity | Since 2014 | Since 2017 | Since 2023 |
| Migration effort | — | Low | Low (compat docs provided) |
| Best for | Correctness, ecosystem | Balanced speed + compatibility | Maximum throughput |

## Decision Matrix: Pick by Workload

| Your situation | Recommended library | Why |
|---|---|---|
| Typical web API, payloads < 5 KB | **serde_json** | SIMD gains are marginal; ecosystem and derive support win |
| Log/metrics pipeline parsing large JSON lines | **simd-json** | SIMD scanning pays off on multi-KB documents; tape API avoids allocation |
| High-throughput data ingestion, CPU-bound | **sonic-rs** | Highest documented deserialization throughput |
| Strict `no_std`/embedded or alloc-only build | **serde_json** | Only one of the three with a supported `alloc`-only mode |
| Simplest migration from existing code | **serde_json** or **simd-json** | `simd-json` ships a serde compatibility layer |
| You need to query one field from a huge document | **simd-json** tape | Tape lets you skip full tree materialization |

## The Contenders in Depth

### 1. serde_json — The Boring, Correct Default

With **5,642 stars** and a commit history stretching back a decade, `serde_json` is the reference implementation of JSON in Rust. It is not merely "good enough" — it is the library that defines the `Value` enum everyone reads and writes, with a `json!` macro for building documents inline:

```rust
use serde::{Deserialize, Serialize};
use serde_json::Result;

#[derive(Serialize, Deserialize)]
struct Person {
    name: String,
    age: u8,
    phones: Vec<String>,
}

fn typed_example() -> Result<()> {
    let data = r#"
        {
            "name": "John Doe",
            "age": 43,
            "phones": ["+44 1234567", "+44 2345678"]
        }"#;

    let p: Person = serde_json::from_str(data)?;
    println!("Please call {} at the number {}", p.name, p.phones[0]);
    Ok(())
}
```

For partially structured data, `serde_json::Value` plus the `json!` macro gives you dynamic manipulation without defining a type:

```rust
use serde_json::json;

let john = json!({
    "name": "John Doe",
    "age": 43,
    "address": { "street": "10 Downing Street", "city": "London" }
});
println!("{}", john["address"]["city"]);
```

The README itself makes the honest claim: serde_json is "comparable to the fastest C and C++ JSON libraries or even 30% faster for many use cases." Its real strength is consistency — no unsafe parsing tricks, a stable `no_std`-friendly build via `default-features = false, features = ["alloc"]`, and zero friction with the wider `serde` ecosystem. Its weakness is that it is a scalar parser: every byte is visited on the general-purpose CPU path.

**Verdict:** keep it as your default until a profiler tells you otherwise.

### 2. simd-json — SIMD, With an Escape Hatch

`simd-json` (1,430 stars, last updated 2026-08-23) is a Rust port of the simdjson algorithm. It uses a two-stage design: a SIMD stage that scans structure at memory bandwidth, then a stage that builds your target type. Crucially, it keeps a serde compatibility layer, so existing derive-based types work with minimal edits:

```rust
use simd_json;
use serde_json::Value;

let mut d = br#"{"some": ["key", "value", 2]}"#.to_vec();
let v: Value = simd_json::serde::from_slice(&mut d).unwrap();
```

Notice the `&mut d` — simd-json parses **in place** and requires a mutable buffer. That is the price of its speed, and it is the single most common migration surprise. If you cannot hand over a mutable `Vec<u8>` (for example, you are decoding straight from a borrowed `&str`), simd-json is the wrong tool.

When you do not need a typed struct, the tape API is the interesting part: it lets you walk structure incrementally and pull out specific fields without materializing a full value tree —

```rust
let mut d = br#"{"the_answer": 42}"#.to_vec();
let tape = simd_json::to_tape(&mut d).unwrap();
let value = tape.as_value();
assert!(value.try_get("the_answer").unwrap().unwrap() == 42);
```

**Verdict:** the sweet spot when you want measurable speedups without leaving the serde world.

### 3. sonic-rs — Built for Throughput

`sonic-rs` (931 stars, updated 2026-09-11) is a newer entry that also uses SIMD, but with a different strategy: it deliberately **avoids** simd-json's two-stage pipeline. Instead it scans JSON directly into your struct without building a temporary tape, and applies SIMD only where it pays: long string parsing, float fractions, field lookup, and whitespace skipping.

```toml
[dependencies]
sonic-rs = "0.3"
```

For untyped access, the crate offers `from_slice_unchecked`, which skips UTF-8 validation when you already know the input is valid:

```rust
// Parses directly into a Rust struct, no intermediate allocation.
let value = sonic_rs::from_slice_unchecked::<MyStruct>(&mut buf)?;
```

The project also publishes a flamegraph comparing its own profile with the simd-json design (`assets/pngs/flamegraph.sonic.svg` in the repo), which is what motivated the single-pass approach.

**Verdict:** the fastest of the three on the project's own benchmark suite, at the cost of being the youngest and smallest community.

## Benchmarks: What the Numbers Actually Say

The numbers below are from the **sonic-rs README's own benchmark run** on an Intel Xeon Platinum 8260 @ 2.40 GHz, using the well-known `serde-rs/json-benchmark` corpus. Treat them as directional, not definitive — the project that publishes a benchmark tends to win it. Still, the pattern is consistent across every JSON document tested.

**twitter.json — deserialize into a struct (lower is better):**

| Parser | Time |
|---|---|
| `sonic_rs::from_slice_unchecked` | **694.74 µs** |
| `sonic_rs::from_slice` | 796.44 µs |
| `simd_json::from_slice` | 1.0615 ms |
| `serde_json::from_str` | 1.3504 ms |
| `serde_json::from_slice` | 2.2659 ms |

**citm_catalog.json — deserialize into a struct:**

| Parser | Time |
|---|---|
| `sonic_rs::from_slice_unchecked` | **1.2271 ms** |
| `sonic_rs::from_slice` | 1.3344 ms |
| `simd_json::from_slice` | 2.0648 ms |
| `serde_json::from_str` | 2.5736 ms |
| `serde_json::from_slice` | 2.9391 ms |

The takeaway is not "sonic-rs is always ~2.9× faster." It is that **both SIMD parsers beat the scalar default on large documents, and the margin grows with payload size**. On a 200-byte API response you will measure noise. On a 4 MB event payload you will measure a CPU core.

One more nuance worth knowing: `serde_json::from_str` often beats `serde_json::from_slice` on these workloads because it avoids UTF-8 validation — which is precisely the check that `from_slice_unchecked` removes in sonic-rs.

## Pitfalls and Migration Notes

- **Mutable buffers are mandatory for SIMD parsers.** `simd_json::from_slice(&mut d)` and `sonic_rs::from_slice` both mutate their input in place. If your data arrives as a borrowed `&str` from a network buffer, you must copy it into a `Vec<u8>` first — and that copy can erase your speedup.
- **Benchmark your real payloads.** Published benchmarks use `twitter.json` and `citm_catalog.json`. Your average document may be 300 bytes, in which case the win is negligible and the complexity is not worth it.
- **Not every SIMD parser validates UTF-8.** `from_slice_unchecked` is *unchecked* — use it only when you control the producer or have already validated the bytes. Feeding it untrusted input is an correctness footgun.
- **`no_std` story differs.** Only `serde_json` supports an alloc-only build officially: `serde_json = { version = "1.0", default-features = false, features = ["alloc"] }`. If you target embedded or a restricted runtime, that alone decides the choice.
- **Error types diverged.** simd-json and sonic-rs have their own error enums. If your code matches on `serde_json::ErrorKind`, budget a refactor pass when migrating.
- **Don't rewrite your API surface for a 5% gain.** Start by caching parsed results or streaming with `serde_json::from_reader`, then escalate to SIMD once the profile justifies it.

## FAQ

### Is serde_json still fast enough in 2026?

For the vast majority of web services, yes. serde_json remains comparable to the fastest C and C++ JSON libraries on many workloads, and its ergonomics and ecosystem reduce defects. Only move to a SIMD parser when a profiler shows JSON deserialization as a top CPU consumer.

### What is the difference between simd-json and sonic-rs?

Both use SIMD instructions, but the design differs. simd-json uses simdjson's two-stage approach: a SIMD structural scan, then a tape you parse into your target type. sonic-rs parses directly into a Rust struct without a temporary tape and applies SIMD only to string parsing, float fractions, whitespace skipping, and field lookup. sonic-rs is generally faster on published benchmarks; simd-json has a longer track record.

### Why do SIMD JSON parsers need a mutable buffer?

They parse in place, reusing the input memory as scratch space and avoiding a second allocation. That is a large part of why they are fast — but it means you must own a mutable `Vec<u8>` rather than passing a borrowed slice.

### Can I migrate from serde_json to sonic-rs without rewriting my structs?

Mostly yes. sonic-rs supports `serde` derive macros and publishes a `serdejson_compatibility` document describing the differences, so `#[derive(Serialize, Deserialize)]` types continue to work. The main changes are the parsing entry points and the error type.

### Should I use the tape API or parse into a struct?

Parse into a struct when you need most fields — it is the fastest path. Use the tape or `try_get` style access when you only need one or two fields out of a large document, since you avoid materializing the rest.

### Does payload size change which library I should pick?

Yes, dramatically. Below roughly 1 KB the difference between scalar and SIMD parsing is often within measurement noise. Above tens of kilobytes, the SIMD advantage grows with document size and can justify the migration.

## Where This Fits in the Rust Ecosystem

If you are assembling a Rust service, JSON parsing is one layer in a stack of choices that all involve the same tradeoff between ecosystem maturity and peak performance. Our [Rust CLI parsers comparison](../2026-08-10-rust-cli-parsers-clap-argh-bpaf/) covers the same tension at the argument-parsing layer, while the [Rust error handling guide](../2026-06-22-rust-error-handling-anyhow-thiserror-eyre-guide/) explains why `anyhow` versus `thiserror` matters once your parser starts returning its own error enum. For the serialization story beyond JSON, see the [binary serialization frameworks comparison](../2026-06-19-binary-serialization-frameworks-bincode-borsh-postcard-rkyv/) — bincode, borsh, postcard, and rkyv are the format-level answer when JSON itself is the bottleneck. And if you need a timezone-safe timestamp inside those payloads, the [Rust datetime libraries comparison](../2026-09-21-rust-datetime-libraries-chrono-jiff-time-hifitime-comparison/) picks apart chrono, jiff, and time.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust JSON Libraries in 2026: serde_json vs simd-json vs sonic-rs (Real Benchmarks)",
  "description": "A practical 2026 comparison of Rust JSON libraries serde_json, simd-json, and sonic-rs, with real published benchmarks, migration pitfalls, and a workload-based decision matrix.",
  "datePublished": "2026-10-03",
  "dateModified": "2026-10-03",
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

## Benchmarking the Byte-Level Parser: A Closer Look

The two SIMD libraries in this comparison disagree about where the CPU should spend its time, and that disagreement is the most interesting technical detail in the whole space. simd-json treats parsing as a two-stage pipeline: first it finds every structural character — braces, brackets, colons, commas, quotes — using vectorized comparisons that process 32 or 64 bytes per instruction, then it walks the resulting index of positions to build output. That is elegant because the SIMD stage is branch-free and predictable, but it means every document pays for a tape that may be thrown away when you only need a few fields.

sonic-rs takes the opposite position. Its maintainers argue that on modern hardware the structural scan is rarely the true hot spot; string handling and number parsing are. So sonic-rs scans JSON directly into the destination structure and reserves vectorized instructions for four specific jobs: parsing long strings, computing the fractional part of floats, locating a specific element or field, and skipping whitespace runs. The payoff is one less intermediate representation to allocate and traverse.

If you want to see the difference rather than read about it, sonic-rs ships flamegraphs for both designs in `assets/pngs/` — a side-by-side profile of the citm_catalog workload, reproduced from the project's official repository:

![sonic-rs deserialization flamegraph from the official repository](/img/screenshots/sonic-rs-flamegraph.jpg "sonic-rs official flamegraph profile for JSON deserialization")

Profile before you migrate, load-test with your own documents, and remember that a parser win of 30% on a workload that is 5% of your runtime is a 1.5% win overall.

For a wider view of how JSON libraries are chosen across languages, our [Go JSON libraries comparison](../2026-07-05-go-json-libraries-encoding-jsoniter-easyjson-gojay-sonic/) walks the same decision in Go, where encoding/json, jsoniter, easyjson, gojay, and sonic make nearly identical promises with different escape hatches. The ecosystem-wide pattern is consistent: the standard library wins on correctness and integration, and a specialized parser wins only once you have proven the hot spot.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
