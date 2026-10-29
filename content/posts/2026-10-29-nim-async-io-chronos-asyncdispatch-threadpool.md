---
title: "Nim Async I/O in 2026: chronos vs asyncdispatch vs threadpool"
date: "2026-10-29"
tags: ["nim", "concurrency", "async", "developer-tools"]
draft: false
cover: "/img/screenshots/nim-logo.jpg"
description: "chronos vs Nim's stdlib asyncdispatch vs threadpool compared with live GitHub data, real async code, the two-dispatcher problem, cancellation gaps and migration advice."
---

You picked Nim because it compiles to a single static binary, runs at C speed, and still reads like Python. Then you added a second HTTP dependency and the build exploded: one library wants `std/asyncdispatch`, the other wants `chronos`, and the two `Future` types are not the same type. There is no adapter, no `await` bridge, and no compiler message that explains what went wrong.

That split is the defining fact of asynchronous Nim in 2026. The language ships an async runtime in its standard library, and the largest production user of Nim — Status, the messaging client — ships a completely separate one. Choosing between them is an architectural decision, not a package preference, because once a codebase commits to a dispatcher, every async dependency has to match.

This guide compares the three ways to do concurrent I/O in Nim — `chronos`, `asyncdispatch`, and plain `threadpool` — with live repository data, real code from each project's own documentation, and the failure modes that cost the most debugging time.

## TL;DR: The Quick Verdict

**Pick `chronos` if you are building a network service and can control your dependency tree.** It has real cancellation, `raises` tracking through async call chains, a built-in TLS stack that does not need OpenSSL, and it is actively developed (`status-im/nim-chronos`, last push **2026-10-27**). Its README labels it *experimental*, and you should take that seriously — but it is the runtime behind a shipping messaging client.

**Pick `asyncdispatch` if you want zero third-party dependencies or you are writing a small tool.** It is in the standard library, it works, and the entire `std/` HTTP client and server stack is built on it. What it lacks is disciplined cancellation and a coherent ecosystem outside `std/`.

**Pick `threadpool` if your work is CPU-bound or calls a blocking C library.** Async cannot make a blocking `read()` non-blocking; a thread can. For heavy parsing, compression, image work or legacy SDK calls, `spawn` plus `FlowVar` is both simpler and faster than any event loop trick.

**And never mix dispatchers in one binary.** That is the single most expensive mistake in this ecosystem.

## Side-by-Side Comparison (live data, October 2026)

| Dimension | chronos | asyncdispatch | threadpool |
|---|---|---|---|
| Repository | `status-im/nim-chronos` | `nim-lang/Nim` (`lib/pure/asyncdispatch.nim`) | `nim-lang/Nim` (`lib/pure/concurrency/threadpool.nim`) |
| Stars | **413** | **18,287** (whole compiler repo) | same repo |
| Last push | **2026-10-27** | **2026-10-29** | **2026-10-29** |
| License | Apache-2.0 / MIT | MIT | MIT |
| Install | `nimble install chronos` | built in | built in |
| Runtime model | single-threaded event loop, owned dispatcher | single-threaded event loop | OS threads with a work queue |
| Cancellation | **first-class** (`CancelledError`, `cancelAndWait`) | limited / cooperative | n/a (threads run to completion) |
| TLS | built in, no OpenSSL required | needs OpenSSL for HTTPS | n/a |
| Error model | `raises` tracking through `Future` | `raises` on `Future` (partial) | exceptions cross thread boundary via `FlowVar` |
| Best at | network servers, clients, timers | stdlib-only tools | CPU-bound work, blocking C calls |

## Decision Matrix: What Should You Actually Reach For?

| Your workload | Choose | Why |
|---|---|---|
| 5,000 concurrent HTTP connections | **chronos** | Cancellation and timeouts you can actually enforce |
| One-shot CLI that fetches a URL | **asyncdispatch** | `std/httpclient` already there, no dependency |
| Parsing 200 MB of JSON per request | **threadpool** | CPU-bound; the event loop would stall |
| Long-poll / WebSocket service | **chronos** | `chronos/apps/http` plus explicit cancellation |
| Wrapping a blocking vendor SDK | **threadpool** | Async cannot unblock a blocking call |
| Mixed: HTTP front end + CPU work | **chronos + threadpool** | Async for I/O, threads for CPU, joined at the handler |
| Strict "no third-party deps" policy | **asyncdispatch** | Everything in `std/` |

Note the last-but-one row: `chronos` and `threadpool` compose fine, because threads are an OS facility rather than a competing event loop. `chronos` and `asyncdispatch` do not compose at all.

## asyncdispatch: The Standard Library Baseline

`std/asyncdispatch` gives you `Future[T]`, the `{.async.}` pragma, `await`, and `waitFor` to enter the loop from synchronous code. It is enough to write a client:

```nim
# file: fetch.nim
import std/[asyncdispatch, httpclient, strutils]

proc fetchTitle(url: string): Future[string] {.async.} =
  let client = newAsyncHttpClient()
  try:
    let body = await client.getContent(url)
    if "<title>" in body:
      result = body.split("<title>")[1].split("</title>")[0]
    else:
      result = "(no title)"
  finally:
    client.close()

when isMainModule:
  echo waitFor fetchTitle("https://nim-lang.org/")
```

The same module gives you an async server (`asynchttpserver`), `asyncdispatch.sleepAsync` for delays, `asyncCheck` for fire-and-forget calls, and `withTimeout` for wrapping a future in a deadline:

```nim
# file: timeout.nim
import std/[asyncdispatch]

proc work(): Future[int] {.async.} =
  await sleepAsync(2000)
  return 42

when isMainModule:
  let f = work()
  let outcome = waitFor withTimeout(f, 500)
  if outcome.timedOut:
    echo "deadline exceeded"
  else:
    echo "result: ", outcome.read
```

Two structural limitations push serious services toward chronos:

1. **Cancellation is shallow.** `withTimeout` abandons *waiting* for a future; it does not cancel the underlying operation. The socket read keeps running, the buffer keeps growing, and the callback still fires. Under load, timeouts convert into leaked work rather than saved capacity.
2. **`raises` tracking stops at the async boundary.** A proc declared `{.async.}` returns `Future[T]`, and the effect system cannot see through `await` in older compilers, so exception guarantees degrade exactly where you need them most.

Neither is a bug report against the standard library — `asyncdispatch` was designed as a small, dependable primitive. It is just not a service framework.

## chronos: A Dispatcher Built for Network Services

`chronos` is the async runtime extracted from the Status client, where it handles long-lived connections, timers and cancellations on mobile hardware. Install it the way the README says:

```bash
nimble install chronos
```

Or pin it in your `.nimble` file:

```nim
# file: myapp.nimble
requires "nim >= 2.0.0"
requires "chronos >= 4.0.0"
```

The HTTP client example below is the one from the project's own tutorial — it fetches a page inside an async proc with a session object that owns its connection pool:

```nim
# file: fetch_chronos.nim
import chronos/apps/http/httpclient

proc retrievePage(uri: string): Future[string] {.async.} =
  let httpSession = HttpSessionRef.new()
  try:
    let resp = await httpSession.fetch(parseUri(uri))
    bytesToString(resp.data)
  finally:
    await httpSession.closeWait()

when isMainModule:
  echo waitFor retrievePage("https://nim-lang.org/")
```

What chronos adds that `asyncdispatch` does not:

- **Real cancellation.** A cancelled `Future` raises `CancelledError` at its next `await` point, and `cancelAndWait` lets you tear down a whole tree of dependent operations. This is what makes per-request deadlines and graceful shutdown possible rather than aspirational.
- **TLS without OpenSSL.** chronos ships its own TLS implementation, which matters when you deploy a static binary to an environment where you cannot install shared libraries.
- **Synchronisation primitives that fit the loop.** `AsyncEvent`, `AsyncQueue`, `AsyncLock` and `AsyncSemaphore` are loop-aware, so backpressure is expressed directly instead of being bolted on with callbacks.
- **A process-oriented dispatch pipeline.** The README advertises "efficient dispatch pipeline with excellent multi-platform support", and in practice that is why the same code runs on Linux servers and on iOS.

The honest caveat is in the badge: `Stability: experimental`. APIs have moved between major versions, the `raises` annotations are strict enough to fight you during a port, and the documentation is thinner than the standard library's. Budget real time for the first service, and pin the version.

![Nim chronos HTTP client tutorial screenshot](/img/screenshots/chronos-http-client.jpg "Browser view from the official nim-chronos HTTP client tutorial")

## threadpool: When Async Is the Wrong Tool

Nim's `threadpool` is a work queue over OS threads. `spawn` schedules a proc, `FlowVar[T]` is the handle, and `^` blocks until the value is ready:

```nim
# file: crunch.nim
import std/[threadpool, strutils, times]

proc expensiveHash(s: string): string =
  # stand-in for CPU-heavy work: compression, parsing, image resize
  result = ""
  var acc = 0'u64
  for i in 0 ..< 20_000:
    for ch in s:
      acc = acc * 31 + uint64(ord(ch))
  result = $acc & "-" & $s.len

when isMainModule:
  var futs: seq[FlowVar[string]]
  for i in 0 ..< 8:
    futs.add spawn expensiveHash("payload-" & $i)
  var total = 0
  for f in futs:
    total += (^f).len
  echo "workers: ", total
```

Build it with threads enabled. Nim 2.x defaults to the ORC memory manager and multi-threading, but if your project supports older toolchains, make it explicit in `config.nims`:

```nim
# file: config.nims
--threads:on
--mm:orc
```

The rules that keep `threadpool` safe:

- **No shared mutable heap objects.** Send `string`, `seq`, numbers or `ptr`-free value types across threads. Sharing a `ref object` across threads is how you get a crash that reproduces once a week.
- **`^` blocks.** Calling it on a hundred flow vars in a loop serialises your parallelism; interleave spawning and reading, or use `await` on a future that joins them.
- **Exceptions travel.** An exception inside `spawn` is re-raised when you read the `FlowVar`, so `try/except` around `^f` is mandatory, not optional.

The cleanest architecture for a real service is a hybrid: chronos handles sockets and timers, and CPU-bound stages are handed to the thread pool with an `AsyncQueue`-bounded handoff. That keeps the event loop responsive no matter how expensive the handler is.

## The Two-Dispatcher Problem

`chronos` and `asyncdispatch` both define a `Future` type, both own an event loop, and neither knows about the other. There is no supported way to `await` a `std/asyncdispatch` future inside a `chronos` proc, and blocking on one from the other deadlocks under load.

The practical consequences, in order of how often they bite:

1. **A dependency silently forces a dispatcher.** You add a database driver written against `asyncdispatch`, then discover every handler must move. Read the driver's imports *before* the architecture review, not after.
2. **"It works in tests."** Tests often run one request at a time, where nesting a `waitFor` inside an async proc appears to work. Under concurrency it starves the loop.
3. **Wrapper libraries pretend to solve it.** Adapters exist, but every one is either a thread hop or a copy of the payload. A thread hop is usually the right answer: run the `asyncdispatch`-based code in a thread and hand results back through a channel.

If you must bridge, bridge at a process or thread boundary, never inside a hot async loop.

## Migration and Coexistence

- **`asyncdispatch` → `chronos`**: change the imports, then let the compiler walk the `raises` annotations. Most ports are mechanical; the painful part is `withTimeout` call sites, which should become real cancellation with `cancelAndWait`.
- **Callbacks → `{.async.}`**: if you have a `proc(cb: proc(resp: Response))` API, wrap it with a `Future` and a completion callback. Do not mix callback completion and `await` in the same function — pick one style per module.
- **Blocking library → thread pool**: wrap the call in `spawn`, expose the result as a future via a channel, and set an explicit worker count. Do not "solve" it with `sleepAsync`.
- **Greenfield service**: start with chronos, keep the thread pool available for CPU stages, and add a rule to CI that forbids `std/asyncdispatch` imports outside `tests/`.

For the layer above the dispatcher, our [Nim web frameworks comparison](../2026-07-25-nim-web-frameworks-jester-prologue-httpbeast-mofuw/) covers which server actually uses which runtime — that detail alone eliminates half the integration pain. If you are still deciding on the language itself, the [systems language comparison](../2026-10-04-vlang-vs-go-vs-c-systems-language-comparison/) sets Nim against its closest competitors, and the [OCaml concurrency comparison](../2026-09-12-ocaml-concurrency-lwt-vs-eio-vs-async/) shows how a very similar Lwt-versus-Eio split played out in another ecosystem.

## Pitfalls That Cost Real Debugging Time

- **Blocking inside an async proc.** A single `readLine()`, `sleep()` or synchronous SQLite call freezes the entire loop — every connection, not just one. Use `sleepAsync` for delays and move blocking calls to threads.
- **Fire-and-forget with `asyncCheck`.** It re-raises the exception into the dispatcher, where it usually kills the process at an unrelated moment. Prefer explicit `await`, or attach a completion callback that logs.
- **Unbounded concurrency.** `for url in urls: asyncCheck fetch(url)` opens one connection per URL. Use a semaphore (`chronos`' `AsyncSemaphore`, or a bounded worker count with threads).
- **Assuming `withTimeout` frees resources.** It abandons the wait, not the work. Close the client in a `finally` block, and prefer cancellation where the runtime supports it.
- **Shared `ref` objects across threads.** This is undefined behaviour, not a warning. Design the boundary around value types and channels.
- **Treating chronos as stable.** It is labelled experimental for a reason. Pin exact versions, read the changelog before upgrading, and keep a thin internal wrapper around its API so a breaking release touches one module.

## FAQ

**Can I use chronos and asyncdispatch in the same project?**
In the same *binary*, effectively no — they are two event loops with two incompatible `Future` types. You can depend on both if they are isolated in separate threads or separate executables, but you cannot `await` across them. Audit your dependency tree for `std/asyncdispatch` imports before committing to chronos.

**Is chronos production-ready despite the "experimental" badge?**
It runs a shipping messaging client at scale, so the runtime itself is battle-tested. The badge reflects API churn rather than reliability. Pin versions, wrap the API, and expect to adjust code on major upgrades — that is the actual cost.

**Why does my async HTTP code hang under load but work in tests?**
Almost always a blocking call inside an async proc, or an unbounded `asyncCheck` flood that starves the loop. Profile with the loop's own metrics (pending callbacks, open handles) and search the handler path for synchronous file, database or `sleep` calls.

**Should I use threads instead of async for an HTTP server?**
For low hundreds of connections, thread-per-connection is simpler and perfectly fine. Beyond a few thousand, memory per thread and context-switch cost dominate, and an event loop wins. The hybrid — chronos for sockets, threads for CPU — is the usual production answer.

**How do I set a timeout in asyncdispatch if `withTimeout` does not cancel?**
Wrap the operation in a proc that checks a deadline between `await` points, close the underlying client on timeout, and treat the abandoned future's result as discarded. If you need enforced deadlines, that gap is precisely why teams move to chronos.

**Does Nim 2.x still need `--threads:on`?**
Nim 2.x enables multi-threading by default with the ORC memory manager, so most projects no longer pass the flag. Keep it explicit in `config.nims` if you support 1.6 toolchains or vendor code compiled with different settings.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nim Async I/O in 2026: chronos vs asyncdispatch vs threadpool",
  "description": "chronos vs Nim stdlib asyncdispatch vs threadpool compared with live GitHub data, real async code, the two-dispatcher problem and cancellation pitfalls.",
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
