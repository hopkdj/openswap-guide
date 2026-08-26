---
title: "Kotlin Concurrency in 2026: kotlinx.coroutines vs RxJava vs Flow — Which One Should You Actually Use?"
date: "2026-08-26"
tags: ["kotlin", "coroutines", "reactive", "concurrency", "jvm"]
draft: false
---

Kotlin's `launch` and `async` have been the default way to write concurrent code on the JVM since 2018, yet a massive amount of production code — especially Android and legacy JVM services — still runs on RxJava's observable streams. If you open almost any large Kotlin codebase today, you will find both `suspend` functions and `Observable` chains living side by side, and teams disagreeing about whether to migrate. This article settles the argument: here is exactly what kotlinx.coroutines, RxJava, and the coroutines-based Flow API are good at, where each one hurts, and how to migrate without rewriting everything at once.

**TL;DR — Quick Verdict:** For new Kotlin code, **kotlinx.coroutines** (13,805 stars, pushed 2026-08-26) is the default — structured concurrency, suspending functions, and compiler-level support make it the idiomatic choice. Use **Flow** (part of kotlinx.coroutines) when you need cold, reactive-style streams with backpressure inside that world. Reach for **RxJava** (48,203 stars, pushed 2026-08-24) only when you are maintaining an existing reactive codebase, or when you genuinely need its 700+ operator catalog and battle-tested backpressure machinery. Do not start new projects on RxJava in 2026.

## The Three Tools, Demystified

It is easy to conflate these three, because they all solve "asynchronous work," but they are not the same kind of thing.

**kotlinx.coroutines** is a language-level concurrency framework. Its core primitive is the `suspend` function — a function that can pause without blocking a thread. You write code that looks sequential, and the compiler rewrites it into state machines. Structured concurrency guarantees that child coroutines are cancelled when their parent scope is cancelled, which eliminates the "orphaned background task" class of bugs.

**RxJava** is a reactive streams library. Its primitives are `Observable`, `Flowable`, `Single`, `Completable`, and `Maybe` — streams that emit values over time, which you transform with operators like `map`, `flatMap`, `debounce`, and `retry`. RxJava is a full implementation of the Reactive Streams specification with a famously enormous operator catalog and strict backpressure semantics.

**Flow** is kotlinx.coroutines' answer to reactive streams: a cold asynchronous stream built on suspend functions. `Flow` is to `kotlinx.coroutines` what `Observable` is to RxJava — but it reuses the coroutines machinery, so it integrates with structured concurrency, cancellation, and suspending code natively.

## Quick Comparison Table

| | kotlinx.coroutines | RxJava 3 | Flow (in kotlinx.coroutines) |
|---|---|---|---|
| GitHub stars | **13,805** | **48,203** | — (same repo as coroutines) |
| Last push | 2026-08-26 | 2026-08-24 | — |
| Core primitive | `suspend` functions, coroutines | Observable/Flowable streams | Cold asynchronous streams |
| Paradigm | Structured concurrency | Reactive streams | Reactive streams + suspend |
| Backpressure | Built-in via suspension | Strict (Flowable) | Built-in via suspension |
| Operator catalog | Small, compose via functions | **700+ operators** | Moderate (100+) |
| Cancellation | Structured, automatic | Manual (Disposable) | Structured, automatic |
| Learning curve | Moderate | Steep | Moderate |
| Language support | Compiler-level (`suspend`) | Library-level only | Compiler-level |
| Interop with suspend code | Native | Awkward (`Single.fromFuture` etc.) | Native |
| Threading model | Dispatchers (IO, Default, Main) | Schedulers (io, computation, trampoline) | Dispatchers |
| JVM / Android / Native | All | JVM + Android | All |

## Decision Matrix — Pick in 10 Seconds

| Use case | Recommended | Why |
|---|---|---|
| New Kotlin project, any kind | **kotlinx.coroutines** | Idiomatic, structured, first-party, smaller mental overhead |
| Cold data streams with operators (UI events, polling) | **Flow** | Reactive style with suspend-function ergonomics |
| Existing RxJava codebase you must maintain | **RxJava** | Rewriting working reactive chains is risk without reward |
| Strict backpressure on huge unbounded streams | **RxJava Flowable** | Proven spec implementation; Flow's suspension is simpler but less configurable |
| Android app with UI updates | **kotlinx.coroutines + Flow** | `Dispatchers.Main`, `lifecycleScope`, first-party support |
| Library authors targeting both worlds | **Flow** | `asFlow()` / `.asObservable()` bridges exist both ways |

## kotlinx.coroutines — The Idiomatic Default

kotlinx.coroutines is developed by JetBrains alongside the Kotlin language itself, and it is the answer to "how should concurrent code look in Kotlin?" The answer: like ordinary code. The official README example demonstrates the entire mental model — two things running concurrently, with the program waiting for both:

```kotlin
suspend fun main() = coroutineScope {
    launch { 
       delay(1.seconds)
       println("Kotlin Coroutines World!") 
    }
    println("Hello")
}
```

`coroutineScope` blocks until all children complete; `launch` starts a fire-and-forget coroutine; `delay` suspends instead of blocking a thread. Add `async`/`await` for results, `Dispatchers.IO` for blocking work, and `CoroutineScope`/`SupervisorJob` for lifecycle management, and you have the full toolkit.

The killer feature is **structured concurrency**: if the scope that launched a coroutine is cancelled, every coroutine under it is cancelled too, and cancellation is cooperative and instant at suspension points. No more leaked background threads when a screen closes or a request times out. The same machinery powers `Flow` and the `suspend`-based IO in Ktor, Exposed, and most of the modern Kotlin ecosystem — our [Kotlin HTTP clients comparison](../2026-08-01-kotlin-http-clients-ktor-fuel-http4k-comparison/) shows how deeply coroutines are woven into Ktor's client.

## RxJava — The 700-Operator Warhorse

RxJava is the reactive library that defined the JVM reactive movement. At **48,203 stars** it is the most-starred project in this comparison by far, and its three major versions have shipped in countless production systems since 2013. RxJava 3.x moved the base classes under `io.reactivex.rxjava3.core` and kept the operator catalog that made it famous:

```java
import io.reactivex.rxjava3.core.*;

public class HelloWorld {
    public static void main(String[] args) {
        Flowable.just("Hello world").subscribe(System.out::println);
    }
}
```

The real power shows in chains that would take dozens of lines of imperative code. RxJava's `Observable.create` gives you a manual emitter with `onNext`, `onError`, and `onComplete`, plus a `Disposable` contract for cleanup:

```java
Observable.create(emitter -> {
     while (!emitter.isDisposed()) {
         long time = System.currentTimeMillis();
         emitter.onNext(time);
         if (time % 2 != 0) {
             emitter.onError(new IllegalStateException("Odd millisecond!"));
             break;
         }
     }
})
.subscribe(System.out::println, Throwable::printStackTrace);
```

With `Flowable`, `Single`, `Completable`, and `Maybe` covering every cardinality, `Schedulers` for threading, and `TestScheduler` for deterministic testing, RxJava is arguably the most complete reactive toolkit on the JVM. Its backpressure is spec-grade: `Flowable` applies `request(n)` semantics with strategies like buffer, drop, and latest — something Flow deliberately simplifies away. Our [Java reactive libraries guide](../2026-08-10-java-reactive-libraries-project-reactor-rxjava-vertx-guide/) compares RxJava against Project Reactor and Vert.x for pure-Java teams.

**The cost:** operator names and marble-diagram thinking are a real learning curve, `Disposable` management is manual (leaked subscriptions are a classic production bug), and every step of a chain allocates. In a coroutines world, RxJava code feels ceremonial — most chains are one `map` and a `flatMap` away from being a plain loop.

## Flow — Reactive Streams Without the Ceremony

Flow is kotlinx.coroutines' native answer to reactive streams, and it is the modern middle ground: reactive operators where you need them, suspend-function ergonomics everywhere else. A Flow is a cold stream — nothing runs until you `collect` it:

```kotlin
fun simple(): Flow<Int> = flow { 
    for (i in 1..3) {
        delay(100) // pretend we are doing something useful here
        emit(i) // emit next value
    }
}

fun main() = runBlocking<Unit> {
    // Collect the flow
    simple().collect { value -> println(value) }
}
```

Because `flow { }` is a suspending builder, you can call `delay`, network calls, or any suspend function inside it — no `map`-to-`Observable` dance required. Backpressure is automatic: `collect` suspends the emitter until the consumer is ready, which is the simplest correct backpressure model that exists. The operator set (`map`, `filter`, `flatMapConcat`, `debounce`, `catch`, `flowOn`, `buffer`, `conflate`, `retryWhen`) covers the 95% of real-world reactive needs.

Flow's greatest strength is that it composes with the rest of the coroutines world: `flowOn` moves work between dispatchers, `catch` handles errors inline, and `asFlow()`/`.asObservable()` bridges exist for interop with RxJava codebases. If you are already using coroutines — and if you write Kotlin in 2026, you are — Flow is the reactive layer that does not ask you to leave the ecosystem.

## Pitfalls and Migration Notes

**1. Do not `collect` on the Main thread blindly.** `collect` runs in the collector's context; network or disk work inside a Flow needs `flowOn(Dispatchers.IO)` (or `Dispatchers.Default`) or you will freeze your UI thread. This is the single most common Flow bug in production.

**2. Structured concurrency is a feature — do not opt out of it casually.** `GlobalScope.launch` exists and you should almost never use it. If you need fire-and-forget work tied to a screen or request lifecycle, create a scope with `SupervisorJob` + a dispatcher and cancel it when the lifecycle ends. Leaked coroutines are the new leaked subscriptions.

**3. RxJava backpressure is strict; Flow's is implicit.** If you migrate a `Flowable` with `onBackpressureBuffer(5000)` to Flow, remember that Flow suspends the producer by default. In most apps that is *better* — it is the exact behavior you wanted — but on unbounded producers (sensor data, high-rate logs) you need `buffer()` or `conflate()` to keep memory bounded.

**4. Cancellation is cooperative.** A coroutine running a CPU-bound loop without suspension points will not cancel until it yields. In hot loops, check `ensureActive()` or use `yield()` so cancellation and the parent scope can interrupt long work.

**5. `runBlocking` is a leak, not a tool.** Using `runBlocking` at the edges of your app (main functions, tests) is correct. Using it inside a coroutine or a library to "wait" for another coroutine is how you get deadlocks and blocked threads. Prefer `withContext` or scope composition.

**6. Migrating RxJava to coroutines: do it stream by stream, not all at once.** The interop bridges make coexistence cheap: `Single.toFlowable()` → `asFlow()`, and the reverse via `.asObservable()`. A pragmatic path is: keep RxJava for complex operator chains, convert simple `Observable`s and `Single`s to suspend functions as you touch them, and forbid new RxJava code in your lint rules. Teams that attempt a big-bang rewrite of 200 reactive chains almost always regress on error handling.

**7. Testing differs in kind.** RxJava has `TestScheduler` for virtual-time operator tests. Coroutines have `runTest` with virtual time for `delay`-based code, and `kotlinx-coroutines-test` provides `StandardTestDispatcher`. The mental model is the same — fast, deterministic tests — but the APIs are not drop-in. Our [Kotlin testing frameworks guide](../2026-07-06-kotlin-testing-frameworks-kotest-mockk-mockito-kotlin/) covers the testing ecosystem around both worlds.

**8. Keep an eye on stack traces.** Coroutine stack traces are reconstructed across suspension points and are generally excellent — but exceptions thrown inside `launch` without a `CoroutineExceptionHandler` propagate to the scope's handler, not the caller. Decide your exception policy at the scope level, not per-coroutine.

## Why Structured Concurrency Matters for Server Code

For server-side Kotlin — Ktor services, Spring WebFlux with Kotlin, worker pipelines — structured concurrency directly controls resource usage. Every coroutine leaked by a careless `GlobalScope` is a thread-pool slot or a database connection held past its deadline. Frameworks like Ktor now treat coroutine scopes as first-class request state: when a request is cancelled, its coroutines are cancelled, and the sockets and clients close with them. That single property removes a whole class of production incidents that plague thread-per-request servers and manually-managed reactive chains.

If you are evaluating the broader Kotlin ecosystem, our [Kotlin serialization comparison](../2026-07-13-kotlin-serialization-libraries-kotlinx-moshi-klaxon/) and the [Kotlin HTTP client guide](../2026-08-01-kotlin-http-clients-ktor-fuel-http4k-comparison/) show how deeply the coroutine model now permeates the language's standard libraries.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Kotlin Concurrency in 2026: kotlinx.coroutines vs RxJava vs Flow",
  "description": "kotlinx.coroutines vs RxJava vs Flow in 2026: structured concurrency, reactive streams, backpressure, and migration guidance with real GitHub stats and code examples.",
  "datePublished": "2026-08-26",
  "dateModified": "2026-08-26",
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

**Q: Is Flow just RxJava for Kotlin?**
A: Conceptually yes — both are cold, operator-rich asynchronous stream abstractions. Technically no: Flow is built on suspend functions and structured concurrency rather than an independent reactive-spec implementation, which means cancellation, threading, and error handling all come from the coroutines machinery instead of a parallel operator universe.

**Q: Should I migrate existing RxJava code to coroutines?**
A: Only incrementally. New code should use coroutines and Flow. Existing, working reactive chains should be migrated one stream at a time via the interop bridges (`asFlow()`, `asObservable()`), especially when you are already touching that code. A big-bang rewrite is rarely justified by the runtime or readability gains.

**Q: What is the difference between `launch`, `async`, and `Flow`?**
A: `launch` starts a fire-and-forget coroutine; `async` starts a coroutine that returns a result via `await()`; `Flow` is a cold stream that emits many values over time and only runs when collected. Use `launch` for side effects, `async` for one-shot parallel results, and `Flow` for streams like UI events, polling, or progress.

**Q: Does Flow support backpressure?**
A: Yes, and in the simplest possible way: the emitter suspends until the collector is ready to receive the next value. If you need buffering, `buffer()`, `conflate()`, and `collectLatest` give you the common strategies from the reactive world without the spec machinery.

**Q: Which is faster — coroutines or RxJava?**
A: For equivalent workloads, coroutines typically allocate less and avoid the per-operator object churn of reactive chains, and suspension is cheaper than scheduler hops. But the difference is rarely the bottleneck in real applications — the bigger win is structured concurrency eliminating leaked work and manual `Disposable` management.

**Q: Can I use RxJava inside suspend functions?**
A: Yes, via `suspendCancellableCoroutine` or the interop helpers in the `rxjava2`/`rxjava3` interop modules (e.g., `Single.await()`, `Observable.awaitFirst()`). This is the standard pattern for calling legacy reactive code from coroutine-based code, and it integrates cancellation correctly.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
