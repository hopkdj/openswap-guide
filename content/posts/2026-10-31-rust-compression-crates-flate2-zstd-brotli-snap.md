---
title: "Rust Compression Crates in 2026: flate2 vs zstd vs brotli vs snap"
date: "2026-10-31"
tags: ["rust", "compression", "performance", "developer-tools", "storage"]
draft: false
cover: "/img/screenshots/rust-zstd-benchmark-chart.jpg"
---

A single `zstd` dependency can cut your archive size by more than half and still run faster than gzip — but only if you picked the right crate, at the right level, for the right payload. Most Rust codebases pick their compression crate by copying whatever their HTTP framework already depended on, then wonder why a 40 GB log partition fills up in eleven days.

The four crates that matter in 2026 are not interchangeable, and the differences are structural, not cosmetic: **flate2** gives you gzip/deflate compatibility with the whole world, **zstd** gives you the best ratio-per-CPU-second with dictionary training, **brotli** gives you maximum ratio for static assets served over HTTP, and **snap** gives you throughput that makes compression nearly free — at the cost of ratio.

## TL;DR — Pick in Thirty Seconds

- **Interop with `.gz` files, HTTP `Content-Encoding: gzip`, or any legacy system?** → **flate2**. It speaks the format everyone already accepts.
- **Compressing anything you store: logs, backups, columnar blobs, event batches?** → **zstd**. Better ratio than gzip at similar speed, and trained dictionaries are a genuine superpower for small records.
- **Pre-compressing static web assets at build time?** → **brotli** at quality 11. This is the one place where its slow encoder is irrelevant and its ratio advantage is real.
- **Compressing data that lives for milliseconds — RPC frames, cache entries, message envelopes?** → **snap**. Ratio is mediocre by design; the point is that it barely costs CPU.
- **Never** pick brotli to compress per-request dynamic responses, and **never** pick snap for long-term storage. Those are the two most common mistakes in Rust services.

## The Four Contenders at a Glance

All figures were pulled live from GitHub and the crates.io registry on 2026-10-31.

| | **flate2** | **zstd** | **brotli** | **snap** |
|---|---|---|---|---|
| Stars | 1,128 | 665 | 967 | 515 |
| Latest version | 1.1.10 | 0.14.3 | 9.1.1 | 1.1.2 |
| Last commit | 2026-10-18 | 2026-10-21 | 2026-10-27 | 2026-07-15 |
| License | Apache-2.0 | BSD-3-Clause | BSD-3-Clause | BSD-3-Clause |
| Implementation | Pure Rust (`miniz_oxide`) by default; optional C backends | Bindings to the C `libzstd` | Pure Rust (optional FFI) | Pure Rust |
| Format | DEFLATE / gzip / zlib | Zstandard | Brotli (RFC 7932) | Snappy |
| Tuning knob | Level 0–10 | Level 1–22 | Quality 0–11 + window 10–24 | Effectively none |
| Dictionaries | No | **Yes — `zstd --train`** | Custom dictionaries (raw API) | No |
| Typical role | Compatibility | Storage + transport | Static assets | Latency-critical |

The star counts are misleading in a useful way: **zstd has the fewest stars of the three general-purpose crates but is the one you should reach for most often.** Stars track how often a crate is a *direct* dependency, and zstd is frequently pulled in transitively behind `async-compression`, `tower-http`, or `parquet` — where it does the work without ever appearing in your `Cargo.toml`.

## Decision Matrix

| Your payload | Pick | Why |
|---|---|---|
| `.log` files appended forever | **zstd** (level 3–6) | Ratio matters, decode speed matters more for grepping |
| HTTP response body with `Accept-Encoding: gzip` | **flate2** | Universal client support; brotli only if you also negotiate `br` |
| Static JS/CSS/HTML at build time | **brotli** (q11) | Best ratio for text; encode cost paid once |
| RPC frame between two Rust services | **snap** | CPU cost near zero; peer has the same crate |
| Small JSON records (100 B–4 KB) stored in a DB | **zstd with a trained dictionary** | Dictionary removes per-record overhead — the single biggest win available |
| Already-gzipped archives you must read | **flate2** (`MultiGzDecoder`) | Handles concatenated members that single-member decoders silently truncate |
| Compressing an S3 object before upload | **zstd** | Server-side decode is cheap; storage cost drops |
| Unknown payload sizes streamed from disk | **zstd streaming** or **flate2 streaming** | Both expose `Read`/`Write` adapters; brotli's writer needs explicit flushing |

## flate2: The Compatibility Layer

flate2 exists so your Rust program can talk to everything that predates it. The default backend is pure Rust (`miniz_oxide`), which means **no C compiler needed and no `cc` in your build pipeline** — a genuine advantage in slim CI images.

The `Cargo.toml` feature flags are where the real decisions live. flate2 1.1.10 declares `default = ["rust_backend", "runtime_detection"]` and lets you swap in a C backend:

```toml
[dependencies]
flate2 = "1.1"

# Or, for a faster DEFLATE implementation at the cost of a C toolchain:
# flate2 = { version = "1.1", default-features = false, features = ["zlib-ng"] }
```

Only one backend should be enabled at a time — the crate's own manifest warns that the selection order is unstable otherwise.

Compressing with the writer API:

```rust
use flate2::write::GzEncoder;
use flate2::Compression;
use std::io::Write;

let mut encoder = GzEncoder::new(Vec::new(), Compression::new(6));
encoder.write_all(b"lots of log lines\n")?;
let compressed: Vec<u8> = encoder.finish()?;
```

Decompressing — and this is where people ship bugs:

```rust
use flate2::read::MultiGzDecoder;
use std::io::Read;

let mut out = Vec::new();
MultiGzDecoder::new(&compressed[..]).read_to_end(&mut out)?;
```

**`GzDecoder` stops at the first gzip member.** A file produced by appending `gzip >> log.gz` repeatedly — exactly what dozens of log rotation setups do — contains multiple members. `GzDecoder` returns the first one and looks successful. `MultiGzDecoder` returns all of them. If you have ever "lost" data in a gzip pipeline without an error, this is why.

**Where flate2 hurts:** ratio. DEFLATE is a 1990s design; at level 9 it still loses to zstd level 3 on most text while being slower. Use it for compatibility, not for efficiency.

## zstd: The Default You Should Reach For

The `zstd` crate wraps Facebook's `libzstd` and exposes three tiers of API, which maps cleanly onto real needs. The official README's own table is the right way to choose:

```rust
// 1. One-shot on a slice or Vec — simplest, allocates the output
let compressed = zstd::stream::encode_all(&data[..], 3)?;
let restored = zstd::stream::decode_all(&compressed[..])?;

// 2. Reusable compressor — avoids re-allocating context per call
use zstd::bulk::Compressor;
let mut c = Compressor::new(3)?;
let a = c.compress(&record_a)?;
let b = c.compress(&record_b)?;

// 3. Streaming — for anything larger than memory
let mut encoder = zstd::stream::Encoder::new(writer, 3)?;
encoder.write_all(&chunk)?;
encoder.finish()?;
```

Level selection is the single highest-leverage knob, and the honest answer is that **level 3 is correct far more often than people expect**. Default `zstd` CLI behavior is level 3; levels 1–5 are the "nearly free" band, 6–12 trade CPU for storage, and 19–22 are archival territory where the encoder gets dramatically slower for a few percent. Level 22 also requires an "ultra" unlock on the CLI (`--ultra -22`), and the decompressor accepts frames at any level you produced.

The feature that no other crate here matches is **dictionary training**:

```bash
# Collect sample records, then train a dictionary
zstd --train samples/*.json -o records.dict --maxdict=65536
```

Then in Rust:

```rust
use zstd::dict::EncoderDictionary;

let dict = EncoderDictionary::copy(&dict_bytes, 3);
let mut encoder = zstd::stream::Encoder::with_prepared_dictionary(Vec::new(), &dict)?;
encoder.write_all(&small_json_record)?;
let compressed = encoder.finish()?;
```

For records in the 100-byte-to-4-kilobyte range, a trained dictionary frequently turns a 1.4x compression into 4x or better, because it pre-seeds the window with common field names and value patterns instead of paying per-record framing overhead. If you are storing millions of small JSON documents, this is the change that pays for itself.

**Where zstd hurts:** it links C code. Cross-compiling to exotic targets (some `musl` targets, `wasm32`) requires care, and `zstd-sys` brings a `cc` build dependency. If your constraint is "pure Rust only, no C toolchain," you want flate2 or brotli instead.

## brotli: Best Ratio, Paid at Build Time

Brotli's encoder has a static dictionary baked into the format — built from real web content — which is why it beats gzip by 15–25% on HTML, CSS, and JavaScript. That advantage is real, and it is also exactly why you should not use it for arbitrary binary data.

The API is a writer adapter. Signature verified against the crate's official example:

```rust
use brotli::CompressorWriter;
use std::io::Write;

let mut out = Vec::new();
{
    // CompressorWriter::new(writer, buffer_size, quality, lgwin)
    let mut w = CompressorWriter::new(&mut out, 4096, 11, 22);
    w.write_all(html.as_bytes())?;
} // drop flushes the remaining window
```

Decoding:

```rust
use brotli::Decompressor;
use std::io::Read;

let mut html = String::new();
Decompressor::new(&compressed[..], 4096).read_to_string(&mut html)?;
```

The two numbers that matter: **quality 0–11** and **lgwin 10–24**. Quality 11 is the maximum-ratio mode and is genuinely slow — think seconds for a few megabytes of text. That is a fine price at build time and an unacceptable one per request. For dynamic responses, quality 4–5 gets most of the benefit at a fraction of the cost; for anything interactive, negotiate `br` alongside gzip and let clients pick.

`lgwin` sets the window size, and therefore memory: `lgwin 22` means a 4 MiB window, `lgwin 24` means 16 MiB. A larger window helps repeated content spread across a big document but forces the decoder to allocate accordingly. For small payloads, a large `lgwin` is pure waste.

**Where brotli hurts:** CPU predictability. Unlike zstd's smooth level curve, brotli's quality scale is non-linear — q10 to q11 can be an order of magnitude slower for single-digit percentage gains.

![Brotli official logo](/img/screenshots/brotli-logo.jpg "Brotli — RFC 7932, with a built-in static dictionary for web text")

## snap: Throughput Over Ratio, On Purpose

Snappy was designed at Google for the case where compression must cost almost nothing: RPC, WAL segments, cache values, columnar blocks read in a tight loop. The Rust `snap` crate (by Andrew Gallant) is a pure-Rust implementation with no C dependency.

The framed API is what you want for streams:

```rust
use snap::write::FrameEncoder;
use std::io::Write;

let mut w = FrameEncoder::new(Vec::new());
w.write_all(&frame_bytes)?;
let compressed = w.into_inner()?;
```

And on the read side:

```rust
use snap::read::FrameDecoder;
use std::io::Read;

let mut out = Vec::new();
FrameDecoder::new(&compressed[..]).read_to_end(&mut out)?;
```

The frame format matters more than it looks: it chunks input into blocks with CRC checksums, so a corrupt block is detectable and stream boundaries survive `Read`/`Write` plumbing. That is why databases and message brokers pick Snappy variants for internal storage.

**Where snap hurts:** ratio, badly. On typical JSON text, Snappy lands far below zstd at similar encode cost — the design bet is that the network or the disk is the bottleneck, not the CPU. Compress a 100 GB archive with Snappy and you will pay for the storage you saved on CPU cycles.

## Benchmark It Yourself Before You Commit

Published ratio charts are useful, but they use corpora that are not your data. Every one of these crates is cheap enough to measure in a unit test. This harness is standalone — add a `[dev-dependencies]` entry per crate and run it against a real sample from your own workload:

```rust
use std::time::Instant;

fn bench<F: Fn(&[u8]) -> Vec<u8>>(name: &str, data: &[u8], f: F) {
    let start = Instant::now();
    let out = f(data);
    let elapsed = start.elapsed().as_secs_f64().max(1e-9);
    let mib_s = (data.len() as f64 / 1_048_576.0) / elapsed;
    let ratio = data.len() as f64 / out.len().max(1) as f64;
    println!("{name:<10} {mib_s:>8.1} MiB/s   ratio {ratio:>5.2}x");
}

fn main() -> std::io::Result<()> {
    let data = std::fs::read("sample.log")?;
    bench("snap", &data, |d| snap::raw::Encoder::new().compress_vec(d).unwrap());
    bench("flate2", &data, |d| {
        let mut e = flate2::write::GzEncoder::new(Vec::new(), flate2::Compression::new(6));
        std::io::Write::write_all(&mut e, d).unwrap();
        e.finish().unwrap()
    });
    bench("zstd-3", &data, |d| zstd::stream::encode_all(d, 3).unwrap());
    bench("zstd-19", &data, |d| zstd::stream::encode_all(d, 19).unwrap());
    Ok(())
}
```

Three rules when reading your own results: **measure decode too** (decode speed is what users feel), **use at least 100 MiB of real data** (small inputs are dominated by fixed overhead), and **never benchmark with `--release` disabled** — debug builds make zstd look catastrophically slow and produce entirely different rankings.

## Pitfalls That Cost Real Debugging Time

### 1. `GzDecoder` silently truncates multi-member files

Already covered, repeated because it is the most common data-loss bug in this space: use `MultiGzDecoder` for anything you did not produce in a single pass.

### 2. `decode_all` needs the frame's content size

zstd frames written with `encode_all` include the decompressed size, letting `decode_all` pre-allocate exactly. Frames produced by a streaming encoder — or by the `zstd` CLI with unknown input size — may omit it, and `decode_all` then fails with a "did not contain content size" style error. Use `zstd::stream::Decoder` (a `Read` adapter) for those, not `decode_all`.

### 3. brotli quality 11 in a request path is an outage waiting to happen

A 200 KB HTML response at q11 can consume tens of milliseconds of CPU. Ten concurrent requests and your latency graph shows a cliff no profiler will explain if you never measured it. Cache the q11 output, serve it as a static asset, or drop to q4–q5.

### 4. Memory grows with level and window

zstd's high levels allocate large match tables; brotli's `lgwin 24` implies a 16 MiB window. Compressing twelve streams concurrently at level 19 on a 512 MB container is a documented path to OOM kills. Cap concurrency or cap the level.

### 5. flate2 backend features are not additive

Enabling both `zlib-ng` and `zlib-rs` on the same crate does not give you "both" — flate2 picks one in an order its own `Cargo.toml` describes as unstable. Pick exactly one backend per workspace, or leave the pure-Rust default alone.

### 6. Snappy is the wrong tool for cold storage

Its ratio penalty compounds with retention. Snappy is a latency optimization for data that will be decompressed within milliseconds; using it on archives means paying for disk forever to save microseconds once.

### 7. Do not compress already-compressed payloads

Compressing a JPEG, an `.mp4`, or an existing `.gz` burns CPU and can *increase* size by a few bytes. Check magic bytes or file extension before you spend cycles, especially in upload pipelines.

## FAQ

**Which Rust compression crate gives the best compression ratio?**

For text and structured data, brotli at quality 11 wins, followed closely by zstd at levels 19–22. The gap between them is usually a few percentage points while brotli's encoder is significantly slower. For real workloads the practical winner is often **zstd with a trained dictionary**, which beats both on small records — a 4x improvement on 1 KB JSON documents is common and no general-purpose setting can match it.

**Is the zstd crate slower than using the zstd CLI?**

No — the crate binds `libzstd` directly, so the encoder is the same C code. Throughput differences you measure usually come from build profile (`--release` vs debug), from calling `encode_all` in a loop instead of reusing a `bulk::Compressor`, or from level choice rather than from the binding.

**When should I use flate2 instead of zstd?**

When interoperability is the requirement rather than efficiency: you must read or write `.gz` files that other tooling produces, you serve `Content-Encoding: gzip` to clients that may not support zstd, or your build must avoid a C toolchain entirely. In a pure Rust-to-Rust pipeline with no external consumers, zstd is almost always the better default.

**Does the snap crate support true streaming?**

Yes. `snap::write::FrameEncoder` and `snap::read::FrameDecoder` are `Write` and `Read` adapters over the framed Snappy format, which splits input into checksummed blocks so stream boundaries are preserved. That framing is also why Snappy tolerates partial reads better than raw block compression — a corrupted block is detected rather than silently producing wrong bytes.

**Can I use brotli for HTTP responses in Rust?**

You can, and you should — but keep two separate code paths. Pre-compress static assets at quality 11 during the build and serve the stored bytes with `Content-Encoding: br`. For dynamic responses, encode at quality 4–5, or skip brotli entirely and use gzip via flate2 for predictable CPU cost. Negotiate with the client's `Accept-Encoding` header rather than assuming support.

**Which crate should I use for a log-shipping agent?**

zstd at level 3, with streaming `Encoder`/`Decoder` rather than one-shot calls. It decodes faster than gzip at equal-or-better ratio, so the receiving side can re-read old segments cheaply, and streaming avoids buffering whole files when a rotation happens mid-upload. Reserve flate2 for the case where a downstream consumer only accepts gzip.

## Related Reading

If you are choosing a compression library in another ecosystem, our [C++ compression library comparison](../2026-06-27-cpp-compression-libraries-lz4-zstd-brotli-snappy-miniz/) covers the same four algorithms with their native C++ bindings. For the operating-system side — the `zstd`, `brotli`, `lz4`, and `gzip` command-line tools, their flags and their trade-offs — see the [Linux compression tools guide](../2026-06-01-linux-compression-tools-zstd-brotli-lz4-gzip/). And if what you actually need is archive container formats rather than the codec inside them, the [archive library comparison](../2026-09-27-archive-libraries-libarchive-sharpcompress-commons-compress-archiver-yauzl-comparison/) covers libarchive, SharpCompress, Commons Compress, archiver, and yauzl.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Rust Compression Crates in 2026: flate2 vs zstd vs brotli vs snap",
  "description": "A practical comparison of Rust compression crates — flate2, zstd, brotli, and snap — with live version data, verified code samples, a decision matrix, dictionary training, and seven pitfalls that cause real production bugs.",
  "datePublished": "2026-10-31",
  "dateModified": "2026-10-31",
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
