---
title: "core.async vs Manifold vs Aleph in 2026: Clojure Async Programming Explained"
date: "2026-09-04"
tags: ["clojure", "async", "concurrency", "websocket", "jvm"]
draft: false
cover: "/img/screenshots/coreasync-cover.jpg"
---

Clojure's superpower on the JVM has always been concurrency, but "concurrent" and "asynchronous" are different beasts. When your service must fan out 10,000 WebSocket connections, stream a large upload with backpressure, or pipeline data between stages without thread-per-connection, you eventually hit the three-letter wall: **core.async**, **Manifold**, or **Aleph**. They are not competitors in the way most libraries compete — they are three layers of the same problem, and in 2026 the ecosystem has settled into a clear pattern: core.async for CSP-style pipelines, Manifold for event-driven abstractions, and Aleph when you need the raw performance of Netty with a Clojure face. This guide shows you exactly where each one wins, with code from the official repos.

## TL;DR: Quick Verdict

**Use core.async when your problem is orchestration**: pipelines, fan-in/fan-out, `go`-block choreography between independent workers. **Use Aleph when your problem is I/O**: serving HTTP/1.1+2 or WebSockets to thousands of clients, or talking to upstream services at Netty speed — it exposes Manifold streams as request bodies, so it pulls Manifold in anyway. **Manifold alone is the abstraction layer** you reach for when writing libraries or when you need deferreds and streams that compose with Aleph. Many production systems use core.async *and* Aleph together, bridged by `manifold.async`.

## Quick Comparison Table

| | core.async | Manifold | Aleph |
|---|---|---|---|
| **GitHub stars** | 2,051 | 1,051 | 2,590 |
| **Last push** | 2026-06 | 2026-03 | 2026-08 |
| **License** | EPL-1.0 | MIT | MIT |
| **Latest version** | 1.9.865 | 0.5.0 | 0.9.11 |
| **Model** | CSP (channels + go blocks) | Deferreds + streams | Netty HTTP/TCP server & client |
| **Threading** | Parking (no thread block) | Executor-managed | Netty event loops |
| **Backpressure** | Buffers (blocking/`offer!`) | Streams (lazy, demand-driven) | Netty + stream flow control |
| **Server capabilities** | None (not I/O) | None (abstractions only) | HTTP/1.1, HTTP/2, WebSockets, TCP, UDP |
| **Ring compatibility** | n/a | n/a | ✅ (drop-in Ring handler) |
| **Status** | Official Clojure contrib | clj-commons, maintained | clj-commons, active |

*Stats fetched via the GitHub API on 2026-09-04.*

## Decision Matrix

| Use Case | Recommendation | Why |
|---|---|---|
| Pipeline of processing stages | **core.async** | `pipeline`, `pipeline-async`, `pipeline-blocking` are purpose-built |
| Fan-out pub/sub within a process | **core.async** | `mult`, `pub/sub`, `mix` — CSP primitives for broadcasting |
| HTTP server or client | **Aleph** | Netty throughput, HTTP/2, WebSocket upgrade out of the box |
| Library exposing async values | **Manifold** | `deferred`/`stream` are the lingua franca of the Aleph ecosystem |
| Thousands of concurrent connections | **Aleph + Manifold** | Event-loop I/O, not thread-per-connection |
| Blocking work mixed into async flow | **core.async** | `pipeline-blocking` + dedicated thread pools |
| Existing Ring app needs speed | **Aleph** | Point Aleph's `start-server` at your Ring handler — no code change |

## core.async: Channels, Go Blocks, and the New Flow API

core.async (2,051 stars, Eclipse Public License) is the official Clojure contrib library for **Communicating Sequential Processes** — Rich Hickey's answer to callback hell. The model: concurrent units communicate over *channels* instead of sharing state; a `go` block parks (not blocks!) when it touches a channel, freeing the thread. From the official `walkthrough.clj`:

```clojure
(require '[clojure.core.async :as async :refer :all])

;; Channels are queue-like. Unbuffered channels rendezvous:
;; producer and consumer must both be present.
(def c (chan))
(go (>! c "hello"))
(assert (= "hello" (<!! (go (<! c)))))

;; Buffered channels decouple producers and consumers:
(def c (chan 10))
(>!! c "hello")          ; blocking put — use only outside go blocks
(assert (= "hello" (<!! c)))
```

The rule of thumb embedded in the API: `<!` and `>!` inside `go` blocks (parking), `<!!` and `>!!` on regular threads (blocking). Composition primitives — `pipeline`, `pipeline-async`, `pipeline-blocking`, `mult`, `pub/sub`, `mix`, `alts!!` — turn channels into a full dataflow toolkit.

Two things make core.async newsworthy in 2026. First, **release 1.9.865 (March 2026)** changed the `io-thread` machinery to use **JVM virtual threads**, and added `datafy` support for channels and buffers — the library is actively evolving rather than frozen. Second, the long-rumored **`core.async.flow`** namespace shipped as an alpha (the API docs label it "Alpha, work-in-progress, names and other details are in flux"): a declarative flow/process model with `create-flow`, `map->step`, `futurize`, pause/resume and live reconfiguration — think dataflow graphs with first-class lifecycle, still built on channels underneath. If you are designing new orchestration code in 2026, `flow` is worth an experiment, but pin it behind a feature flag: alpha means breaking changes.

## Manifold: Deferreds and Streams as the Lingua Franca

Manifold (1,051 stars, MIT, maintained under clj-commons) is Zach Tellman's elegant middle layer: **`deferred`** (a composable future — success, error, cancelable, with `let-flow` for dependency graphs) and **`stream`** (an asynchronous, potentially infinite sequence with demand-based backpressure). From the official README:

```clojure
(require '[manifold.deferred :as d])

(def d (d/deferred))
(d/success! d :foo)
@d  ; => :foo
```

Where core.async models *communication*, Manifold models *values over time*: a deferred is one value later, a stream is many values later. Streams are lazy — a consumer pulls (or a producer pushes with `put!` respecting the consumer's demand), which is exactly the semantic you want for HTTP response bodies and WebSocket message flows. Manifold also ships a bridge namespace, **`manifold.async`**, which converts between Manifold streams and core.async channels (`->source`, `->sink`, `to-channel`, `from-channel`), so the two models interoperate rather than compete. Because Aleph is built directly on Manifold, any code that touches an Aleph request body is already speaking Manifold — which is why "learn Manifold" is really "learn how to read your HTTP responses."

## Aleph: Netty Performance with Ring Familiarity

Aleph (2,590 stars, MIT — the most-starred of the three, last push August 2026) wraps **Netty** in Clojure and exposes an HTTP server and client that speak Ring's handler language. You point `start-server` at an ordinary Ring handler and get HTTP/1.1, HTTP/2 (with an SSL context), WebSockets, and streaming bodies:

```clojure
(require '[aleph.http :as http])

(defn handler [req]
  {:status 200
   :headers {"content-type" "text/plain"}
   :body "hello!"})

;; HTTP/1.1 on :8080
(http/start-server handler {:port 8080})

;; HTTP/2 requires TLS:
;; (def my-ssl-context ...)
(http/start-server handler {:port 443
                            :http-versions [:http2 :http1]
                            :ssl-context my-ssl-context})
```

The magic — and the trap — is in the `:body`. Aleph request/response bodies are **Manifold streams**: `:body` on a request is a stream of byte chunks, and returning a stream as `:body` streams the response with backpressure. That is what lets one Aleph process hold tens of thousands of open connections without a thread each: your handler runs on Netty's event loops, and anything slow must be handed off (to core.async `pipeline-blocking`, a Manifold executor, or a virtual-thread pool) rather than blocking the loop. Aleph also ships TCP and UDP clients/servers with the same streaming model, making it the generalist's choice for high-throughput socket work in Clojure.

## Pitfalls and Gotchas

1. **Never mix parking and blocking ops.** `<!!` inside a `go` block, or `>!` outside one, throws or deadlocks. The `!` vs `!!` suffix is a correctness contract: parking ops must only appear in go/`thread` contexts. This is the #1 bug in real core.async codebases.
2. **Don't do blocking I/O in a `go` block.** A `go` block runs on a small shared thread pool (CPU-count sized). A `Thread/sleep` or a blocking JDBC call inside `go` starves the pool and stalls unrelated channels. Use `thread`, `pipeline-blocking`, or `io-thread` (which, as of 1.9.865, runs on virtual threads) for blocking work.
3. **Channels are not queues for everything.** Using an unbuffered channel as a work queue makes throughput depend on rendezvous timing; prefer bounded buffers + `offer!`/`poll!` when you need non-blocking admission control, and always `close!` channels or you leak parked producers.
4. **Aleph handlers must not block the event loop.** A Ring handler that sleeps or does synchronous DB access will freeze connections for everyone. If your handler is synchronous, wrap it with `aleph.http/wrap-ring-handler`-style offloading or run the blocking work in an executor and return a deferred/stream.
5. **Manifold streams are single-consumer.** You cannot re-read a stream; if two consumers need the data, `stream/source-only`+`stream/connect` to two sinks, or buffer explicitly. Re-consuming a consumed stream yields `nil` silently — the classic "my second client gets nothing" bug.
6. **Version alignment:** Aleph 0.9.x and Manifold 0.5.x must be compatible; an old Manifold pinned by another dependency will surface as confusing `NoSuchMethodError` from Netty or manifold internals. Run `clj -Stree`/`lein deps :tree` and check for duplicate manifold/aleph coordinates.
7. **`core.async.flow` is alpha.** Its API docs literally warn that names are in flux. Use it behind a feature toggle; do not build a product on it without pinning the exact version.

## Which One Should You Actually Use?

In 2026 the pragmatic answer is **both core.async and Aleph**, with Manifold as the glue. Serve HTTP and WebSockets with Aleph (Ring-compatible, Netty-fast); model internal fan-out and pipeline processing with core.async; bridge the two via `manifold.async` where a connection's message flow needs to enter a channel pipeline. If you are writing a library, expose Manifold deferreds/streams — that is what the Aleph ecosystem consumes natively. Skip core.async only if your entire problem is request/response I/O; skip Aleph only if you never serve sockets and are happy with a plain HTTP client. The three libraries are not rivals — they are the layers of one coherent stack, and knowing which layer your problem lives in is the actual skill.

For the Web framework layer that sits on top of these, our [Clojure Web framework comparison (Ring, Compojure, Reitit)](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/) shows how Aleph serves Ring handlers inside the standard Clojure Web stack. If you are evaluating async models across languages, the [C# async dataflow guide (TPL Dataflow, Channels, Rx.NET)](../2026-08-30-csharp-async-dataflow-channels-tpl-dataflow-rxnet-comparison/) is the closest structural sibling — .NET Channels map almost one-to-one onto core.async concepts — and the [Scala effect systems comparison (cats-effect, ZIO, Monix)](../2026-09-03-scala-effect-systems-cats-effect-zio-monix-comparison/) covers the typed-effect alternative to loose channels.

## FAQ

**What is the difference between core.async and Aleph?**
core.async is a concurrency model (CSP channels and go blocks) for orchestrating work inside your process; it does no I/O itself. Aleph is an I/O layer — a Netty-based HTTP/TCP server and client — that uses Manifold streams for bodies. They solve different problems and are commonly used together.

**When should I use Manifold instead of core.async?**
Use Manifold when you are building on Aleph or writing libraries that expose async values: its `deferred` and `stream` types are what Aleph's request/response bodies use. Use core.async when you want CSP primitives (channels, mult, pub/sub, pipelines) for process-internal orchestration.

**Is Aleph a drop-in replacement for other Clojure HTTP servers?**
Almost. It serves standard Ring handlers, so existing middleware stacks work. The differences appear with streaming bodies (Manifold streams) and WebSockets, where Aleph's model is more explicit than libraries that hide the socket behind callbacks.

**Does core.async still matter now that Java has virtual threads?**
Yes — and they are complementary. Virtual threads make blocking code cheap, which is why core.async 1.9.865 runs its `io-thread` on virtual threads. But channels, parking, and compositional primitives (mult, pipeline, alts!) remain a higher-level, Clojure-idiomatic orchestration model that raw threads do not provide.

**What is core.async.flow?**
A new alpha dataflow API (added in 2026) for declarative flows with steps, pause/resume, and live reconfiguration. It is explicitly work-in-progress — names and semantics may change — so treat it as experimental.

**Which license should I care about?**
core.async is EPL-1.0 (same as Clojure itself), while Manifold and Aleph are MIT. All three are fine for commercial use; EPL carries weak copyleft terms only if you modify and redistribute the library itself.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "core.async vs Manifold vs Aleph in 2026: Clojure Async Programming Explained",
  "description": "When to use core.async channels, Manifold deferreds and streams, or the Aleph Netty HTTP server in Clojure. Real code from official repos, 2026 updates including core.async.flow, decision matrix, and concurrency pitfalls.",
  "datePublished": "2026-09-04",
  "dateModified": "2026-09-04",
  "author": {"@type": "Organization", "name": "OpenSwap Guide"},
  "publisher": {"@type": "Organization", "name": "OpenSwap Guide"},
  "mainEntityOfPage": "https://www.pistack.xyz/posts/2026-09-04-clojure-async-libraries-core-async-manifold-aleph-comparison/"
}
</script>

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
