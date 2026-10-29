---
title: "Haskell Streaming Libraries in 2026: conduit vs pipes vs streamly"
date: "2026-10-29"
tags: ["haskell", "functional-programming", "developer-tools", "streaming"]
draft: false
cover: "/img/screenshots/streamly-streams.jpg"
description: "conduit vs pipes vs streamly compared with live GitHub data, real streaming code from each project's own docs, resource-safety pitfalls, and a migration path for large-file pipelines."
---

Your nightly ETL job reads a 40 GB CSV export, and `readFile` plus `length` sends the machine into swap. That is the moment most Haskell teams discover that lazy `ByteString` is not a streaming abstraction — it is a promise the runtime may not keep. You need a library that guarantees constant memory, closes file handles deterministically, and lets you compose sources, transforms and sinks without hand-rolling bracket gymnastics.

Three libraries dominate that space in 2026: **conduit**, **pipes** and **streamly**. They solve the same problem with very different philosophies — and one of them is now dramatically more active than the other two. This guide compares them with live repository data and real code taken from each project's own documentation, then walks through the pitfalls that actually bite in production.

## TL;DR: The Quick Verdict

**Pick streamly if you are starting fresh in 2026.** It is the only one of the three with commits in 2026, it fuses pipelines into C-like loops, and it ships declarative concurrency (concurrent `mapM`, `append`, interleaving) that conduit and pipes make you build by hand.

**Pick conduit if your codebase already lives in the Yesod/Persistent orbit**, or if you need the largest catalogue of ready-made integrations (HTTP, CSV, XML, SQL, compression). It is boring, documented to death, and every streaming question on Stack Overflow has a conduit answer.

**Pick pipes if you want the cleanest mental model and do not need concurrency.** `yield`/`await` and `>->` are the most teachable primitives in the ecosystem — but the last commit to `Gabriella439/pipes` was in **October 2022**, so treat it as a stable, feature-frozen tool rather than an evolving one.

Do not pick a streaming library at all if your data fits comfortably in memory. Every one of these adds a type-level learning curve, and `Data.Text.IO.readFile` on a 50 MB file is still the right answer.

## Side-by-Side Comparison (live data, October 2026)

| Dimension | conduit | pipes | streamly |
|---|---|---|---|
| GitHub repo | `snoyberg/conduit` | `Gabriella439/pipes` | `composewell/streamly` |
| Stars | **913** | **493** | **927** |
| Last push | 2025-06-26 | 2022-10-15 | **2026-10-28** |
| License | MIT | BSD-3-Clause | Apache-2.0 (core: BSD-3) |
| Core abstraction | `ConduitT i o m r` | `Proxy a' a b' b m r` | `Stream m a` / `Fold m a b` |
| Operator style | `.|` pipe operator | `>->` composition | `S.map`, `S.filter`, `S.fold` |
| Stream fusion | Yes (conduit 1.3+) | Yes (shortcut fusion) | Yes, plus loop fusion for arrays |
| Built-in concurrency | Via `conduit-extra`/STM | Manual (`pipes-concurrency`) | **Declarative, in core** |
| Ecosystem breadth | Very large | Moderate | Growing, focused |
| Learning curve | Medium | Low–medium | Medium |
| Best fit | Existing Yesod/SQL apps | Teaching, small pipelines | New high-throughput services |

## Decision Matrix: Which One Fits Your Job?

| If your situation is… | Choose | Because |
|---|---|---|
| New service, 10k+ events/sec, needs parallelism | **streamly** | Concurrent stream combinators are built in; fused loops cut allocation |
| Existing Yesod app with `conduit` already in the dependency tree | **conduit** | Zero-cost adoption; `conduit-extra` covers HTTP/CSV/zip |
| Teaching a team what streaming means | **pipes** | `await`/`yield` make backpressure visible in the types |
| Large CSV/JSON import with strict memory ceiling | **conduit** or **streamly** | Deterministic finalizers and chunked `ByteString` handling |
| You need `pipes-concurrency`-style mailboxes only | **pipes** | Mature, stable, no churn |
| You want one library to also do array processing and folds | **streamly** | `streamly-core` unifies streams, folds and unboxed arrays |

## conduit: The Boring Choice That Ships

conduit's model is a stack of three roles — **Source**, **Conduit** (transform) and **Sink** (consume) — unified into a single `ConduitT i o m r` type. You build a pipeline with the `.|` operator and run it with `runConduit`.

```haskell
-- file: app/Main.hs
{-# LANGUAGE OverloadedStrings #-}
module Main (main) where

import Conduit
import Data.Text (Text)
import qualified Data.Text as T

main :: IO ()
main = do
  -- Read a large CSV, keep only rows mentioning "timeout",
  -- count them, and never hold more than one chunk in memory.
  n <- runConduitRes
         $ sourceFileBS "logs/2026-10-29.csv"
        .| linesC
        .| filterC (T.isInfixOf "timeout")
        .| lengthC
  print n
```

Add it to a Cabal project the way the README instructs — conduit 1.3 is the long-term-support line and is what `conduit-extra` targets:

```cabal
-- file: my-project.cabal
build-depends:
    base            >=4.14 && <5
  , conduit         ^>=1.3
  , conduit-extra   ^>=1.3
  , text
  , bytestring
```

Two things make conduit pleasant in practice. First, `runConduitRes` runs in `ResourceT`, so file handles are released on exception, not on garbage collection — the single most common source of "too many open files" in naive streaming code. Second, `conduit-extra` gives you `sourceHandle`, `sinkHandle`, `linesUnboundedAsciiC`, gzip/zlib conduits and an HTTP source, which means the 80% case needs no new dependencies. Version 1.3 also introduced **stream fusion**: `.|` pipelines are rewritten into a single loop rather than nested function calls, which removed most of the historical performance gap versus hand-written loops.

The cost is conceptual overhead. `ConduitT i o m r` has four parameters, `connect`/`fuse` semantics are not obvious on day one, and error messages involving `MonadResource` can be rough. But the ecosystem is enormous, the documentation is thorough, and it is the only one of the three that inherits an entire web framework's worth of integrations.

## pipes: The Cleanest Mental Model

pipes reduces streaming to two primitives: a producer `yield`s, a consumer `await`s, and `>->` connects them. Everything else — `Pipes.Prelude`, `Pipes.Group`, `Pipes.Parse` — is derived from that.

```haskell
-- file: app/Echo.hs
module Main (main) where

import Pipes
import qualified Pipes.Prelude as P

main :: IO ()
main = runEffect $ P.stdinLn >-> P.takeWhile (/= "quit") >-> P.stdoutLn
```

That three-stage pipeline is straight from the project README, and it is the best teaching artifact in the Haskell streaming world: you can *see* backpressure, because `stdinLn` cannot outrun `stdoutLn`. Folds are equally direct:

```haskell
-- file: app/Count.hs
{-# LANGUAGE OverloadedStrings #-}
module Main (main) where

import Pipes
import qualified Pipes.Prelude as P
import qualified Pipes.ByteString as PB

countErrors :: IO Int
countErrors =
  P.length
    $ PB.lines PB.stdin
    >-> P.filter ("ERROR" `elem`)   -- simplified predicate
```

Install it the way the README says — it is on Hackage, so `cabal install pipes` is enough, and the tutorial ships with the package.

The trade-off is momentum. `Gabriella439/pipes` last saw a push in **October 2022**, and `pipes-concurrency`, `pipes-safe` and `pipes-bytestring` follow the same cadence. Nothing is broken — the library is small, total, and stable — but you should not expect new combinators, GHC-version-specific optimizations, or fixes for edge cases discovered after 2022. If your organisation has a policy of "dependencies must have commits in the last 18 months", pipes fails that policy today.

Where pipes still wins outright: **reasoning about resource safety and composition in review**. A `Proxy` pipeline can be read top to bottom by a reviewer who has never seen the library, which is not true of `ConduitT` newtype stacks or streamly's combinator zoo.

## streamly: Fusion, Folds and Declarative Concurrency

streamly is the outlier — and in 2026 it is the only actively developed option of the three, with a push on **2026-10-28** and 927 stars. Its pitch is "idiomatic Haskell with C-like performance", and unlike conduit and pipes it is not just a stream type: `streamly-core` unifies streams, folds, unboxed arrays and bytes, while the main `streamly` package layers concurrency on top.

![Streamly stream pipeline architecture](/img/screenshots/streamly-streams.jpg "Official streamly stream architecture diagram from the project repository")

```haskell
-- file: app/Aggregate.hs
{-# LANGUAGE OverloadedStrings #-}
module Main (main) where

import qualified Streamly.Data.Fold as Fold
import qualified Streamly.Data.Stream as Stream
import qualified Streamly.Data.Stream.Prelude as Stream

main :: IO ()
main = do
  -- Sum the third column of a big TSV using a fused stream -> fold pipeline.
  total <- Stream.fold Fold.sum
         $ Stream.mapMaybe parseThird
         $ Stream.lines Stream.readFile "sales.tsv"
  print (total :: Double)

parseThird :: String -> Maybe Double
parseThird line =
  case drop 2 (splitOn '\t' line) of
    (x:_) -> readMaybe x
    _     -> Nothing

splitOn :: Char -> String -> [String]
splitOn c s = case break (== c) s of
  (a, [])     -> [a]
  (a, _:rest) -> a : splitOn c rest
```

Dependency line, per the project README (streamly 0.9+ split into `streamly-core` and `streamly`):

```cabal
build-depends:
    base           >=4.14 && <5
  , streamly       ^>=0.10
  , streamly-core  ^>=0.3
```

What streamly buys you that the other two do not:

- **Concurrency in the type system, not in a side package.** `Stream.mapM` runs effects one at a time; `Stream.parMapM` variants run them concurrently with a configurable bound, and `Stream.concurrent`/`Stream.merge` compose whole streams in parallel. In conduit you assemble this from `mapConcurrently` plus a queue; in pipes you reach for `pipes-concurrency`.
- **Aggressive fusion.** The project's own benchmark page claims fused loops can be up to **100× faster** than libraries without stream fusion for certain numeric workloads. Treat that as a vendor claim, not a benchmark you can copy — but the underlying technique (rewriting `Stream` pipelines into a single loop at compile time) is real and visible in Core output.
- **Folds as first-class citizens.** `Fold m a b` lets you compose sinks with `Fold.teeWith`, `Fold.parTeel` and `Fold.groupBy`, which is exactly what "average latency per route and overall throughput in one pass" needs.

The cost: streamly's API surface is large and still moving (the README ships an "Upgrading to 0.9.0+" guide precisely because it moved), and its type errors are the least friendly of the three. Budget a day for the first real pipeline, and pin the version in production.

## Performance and Memory: What Actually Matters

Star counts do not tell you which library will survive your dataset, so measure the four things that break in production:

1. **Chunk size, not stream size.** All three libraries are fine with 40 GB files *if* you stream `ByteString` chunks and never call a strict fold that materialises everything. The failure mode is always `Data.ByteString.Lazy.readFile` followed by `BL.length`, which builds the entire file in memory and then throws it away.
2. **Finalizer timing.** `runConduitRes` and `Stream.drain` release resources deterministically. Hand-rolled `bracket` around a lazy list does not — the handle closes when the list is forced, which may be never.
3. **Allocation per element.** Fusion removes intermediate lists, but only when the pipeline stays inside the library's own combinators. Dropping out to `map` on a plain list midway (`Stream.fromList . map f . toList`) discards every fusion guarantee.
4. **Concurrency bounds.** Unbounded `parMapM` on a 200k-file directory tree will exhaust file descriptors long before it exhausts CPU. Always set an explicit concurrency limit — streamly's `maxThread`/`maxBuffer`, or `mapConcurrently` with a semaphore.

A practical benchmark harness: generate a 2 GB NDJSON fixture once, run each pipeline three times with `+RTS -s`, and compare **maximum residency** and **total alloc** rather than wall clock. Wall clock on a warm page cache hides allocation regressions; `-s` does not.

## Migration and Coexistence Strategies

Nobody rewrites a working pipeline for elegance, so plan for coexistence:

- **conduit → streamly**: wrap at the boundary. Convert with `Stream.unfoldrM` over `conduit`'s `sourceToList` for small sources, or run the conduit pipeline and feed its output handle to `Stream.readFile` for large ones. Migrate leaf jobs first, keep the Yesod request path on conduit until the new code has survived a month of production traffic.
- **pipes → conduit**: `Pipes.Prelude.toListM` then `yieldMany` is fine up to a few hundred MB, and unacceptable above it. For genuinely large streams, port the pipeline rather than bridging it — pipes' `Proxy` and conduit's `ConduitT` are both "a coroutine in a monad", so the port is mechanical even when it is tedious.
- **New code in an old codebase**: pick whichever library is *already* in `build-depends`. Adding a second streaming library to a service is a real maintenance tax: two sets of operators, two sets of tutorials, two sets of bugs.

For the surrounding tooling, our [Haskell serialization comparison](../2026-10-25-haskell-serialization-aeson-cassava-cborg-serialise/) covers the decode side of these pipelines, and the [testing guide](../2026-08-01-haskell-testing-frameworks-hspec-quickcheck-tasty-hunit/) shows how to property-test stream transformations before they touch production data. If your streams carry effects that need tracking, the [effect systems comparison](../2026-09-19-haskell-effect-systems-effectful-polysemy-fused-effects-mtl/) explains where `MonadResource` and friends fit.

## FAQ

**Is streamly production-ready in 2026?**
streamly-core is stable and widely used; the higher-level `streamly` package moves faster and has shipped breaking changes (see its 0.9 upgrade guide). Pin exact versions, read the changelog before upgrading, and keep concurrency predicates behind your own thin wrapper so a future API change touches one module.

**Why is `pipes` still recommended if it has not been updated since 2022?**
Because it is finished, not abandoned. The API is small, total and well specified, and it compiles against current GHC releases. The risk is not correctness — it is that nobody will fix a newly discovered edge case or add a combinator you need. For teaching, review-friendly pipelines and small tools, that risk is acceptable.

**Can I use conduit and streamly in the same project?**
Yes, and many teams do during migration. Both are ordinary libraries with no global state. Convert at process boundaries (files, handles, queues) rather than element-by-element inside a hot loop, because bridging per element throws away fusion in both libraries.

**Which library handles backpressure best?**
All three provide it structurally: a sink pulls, so a fast source cannot overrun a slow consumer. The difference appears when you add concurrency. streamly exposes bounded concurrent combinators directly; conduit and pipes require you to build the bound yourself with `TBQueue` or `pipes-concurrency` mailboxes.

**Do I need a streaming library for a 100 MB file?**
No. `Data.ByteString.Lazy.readFile` plus a strict fold is simpler and fast enough. Adopt a streaming library when files exceed available memory, when you must process unbounded input (sockets, stdin, tail -f), or when resource-release timing matters — for example, closing a database cursor before the connection returns to the pool.

**What about `conduit` versus plain `streaming` (the `streaming` package)?**
`streaming` is a smaller, more mathematically elegant library with a loyal following, but it has an even smaller ecosystem than pipes. If you are choosing today and want ecosystem breadth plus active maintenance, the realistic shortlist is conduit and streamly.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Haskell Streaming Libraries in 2026: conduit vs pipes vs streamly",
  "description": "conduit vs pipes vs streamly compared with live GitHub data, real streaming code, resource-safety pitfalls and a migration path for large-file pipelines.",
  "datePublished": "2026-10-29",
  "dateModified": "2026-10-29",
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
