---
title: "Lwt vs Eio vs Async in 2026: Which OCaml Concurrency Runtime Should You Actually Use?"
date: "2026-09-12"
tags: ["ocaml", "concurrency", "developer-tools", "functional-programming", "async"]
draft: false
---

You ship an OCaml service that handles 8,000 concurrent connections on a single core, then you upgrade to OCaml 5 and discover your entire `Lwt` codebase cannot use the other 15 cores without rewriting the I/O layer. That is the moment every OCaml team hits the same wall: **the concurrency runtime you picked in 2019 now decides your multicore roadmap in 2026.** There are three credible answers — Lwt, Eio, and Async — and they disagree about almost everything: syntax, scheduler design, ecosystem, and whether "async" should even be a color in your type signatures.

**Quick verdict:** Pick **Eio** for anything new on OCaml 5.2+ where you want direct-style code, real multicore parallelism, and no monadic plumbing. Pick **Lwt** if you depend on the Ocsigen stack (Eliom, js_of_ocaml, Irmin) or need the largest body of existing bindings. Pick **Async** only if you are already inside the Jane Street ecosystem — Core, `Incremental`, `Iron`, and the `ppx_jane` suite — because its value is the ecosystem coupling, not the scheduler itself.

## The Three Runtimes at a Glance

| Dimension | **Lwt** | **Eio** | **Async** |
|---|---|---|---|
| Stars (Sep 2026) | **792** | 723 | 275 |
| Last commit | 2026-08-19 | **2026-09-11** | 2026-07-10 |
| Programming model | Monadic promises (`let%lwt`) | Direct style, effect handlers | Monadic deferreds (`let%bind`) |
| Minimum OCaml | 4.08+ | **5.2.0+** (5.5 recommended) | 4.14+ / 5.x |
| Multicore parallelism | Opt-in preemptive threads | **Native, first-class** | Domains via `Async` + Core |
| Ownership | Ocsigen project | ocaml-multicore org | Jane Street |
| IO backends | `libev` / `Lwt_unix` | **io_uring** (Linux), posix, Windows | `libev`-based `Async_unix` |
| Cancellation | `Lwt.cancel`, `Lwt.pick` | Structured (`Switch`) | `Deferred` + `Monitor` |
| Licence | MIT | **MIT** | MIT |

The star counts are real, pulled live from GitHub this month — and note how close Lwt and Eio are. Star count is a lagging indicator of a decade of production use versus eighteen months of rapid design iteration. **Do not pick on stars.** Pick on whether your code needs to be monadic.

## Decision Matrix: Match the Workload to the Runtime

| Your situation | Use | Why |
|---|---|---|
| New HTTP/gRPC service on OCaml 5.5 | **Eio** | Direct style, io_uring backend, structured concurrency |
| Existing Eliom / Ocsigen site | **Lwt** | Eliom *is* Lwt; porting means rewriting the framework |
| Trading engine already using Core | **Async** | Zero-friction interop with `Incremental` and `Iron` |
| Library that must support OCaml 4.14 | **Lwt** | Eio requires 5.2+; Async requires the Jane Street floor |
| CPU-bound data pipeline with IO | **Eio** | Domain pools without thread-pool tuning |
| You want the shortest learning curve | **Eio** | No monad, no `let%lwt`, no syntax extension |
| Mixed Lwt and modern code | **Lwt + Eio bridge** | Migrate leaf services first, keep the monad at the edges |

## Lwt — The Battle-Tested Promise Library

Lwt gives you exactly one type: the *promise*, a value that will be resolved later. Creating a promise spawns a computation; waiting on it is `let%lwt` with the `lwt_ppx` syntax extension, or `let*` from `Lwt.Syntax` if you refuse preprocessing. Because OCaml code runs single-threaded by default, you never think about locks — until you `Lwt_preemptive.detach` and suddenly you do.

A realistic Lwt program with a timeout, taken from the project's own README:

```ocaml
let () =
  let request =
    let%lwt addresses = Lwt_unix.getaddrinfo "google.com" "80" [] in
    let google = Lwt_unix.((List.hd addresses).ai_addr) in

    Lwt_io.(with_connection google (fun (incoming, outgoing) ->
      write outgoing "GET / HTTP/1.1\r\n";%lwt
      write outgoing "Connection: close\r\n\r\n";%lwt
      let%lwt response = read incoming in
      Lwt.return (Some response)))
  in

  let timeout =
    Lwt_unix.sleep 5.;%lwt
    Lwt.return_none
  in

  match Lwt_main.run (Lwt.pick [request; timeout]) with
  | Some response -> print_string response
  | None -> prerr_endline "Request timed out"; exit 1
```

Install it the boring, reliable way, then build with dune:

```bash
opam install lwt lwt_ppx
```

```lisp
;; dune
(executable
 (name main)
 (libraries lwt lwt.unix))
```

`Lwt.pick` is the part teams love: racing a request against a timeout is one function call, and the loser is cancelled. The part teams learn to hate is that **every function in the call graph becomes `'a Lwt.t`** — the viral type. Adding one dashboard endpoint can turn a synchronous helper into monadic plumbing across six files. Lwt is not slow (it is extremely fast, and battle-hardened since 2007); it is *contagious*.

## Eio — Direct-Style IO With Effect Handlers

Eio is the successor design from the OCaml multicore effort. There is no promise type in your signatures: code that would be `let%lwt` in Lwt is simply sequential code, and the scheduler hides in an effect handler installed by `Eio_main.run`. This is why Eio feels like Python's asyncio written properly, or Go without goroutine leaks.

```ocaml
# #require "eio_main";;
# open Eio.Std;;
```

```ocaml
let main out =
  Eio.Flow.copy_string "Hello, world!\n" out

let () =
  Eio_main.run @@ fun env ->
  main (Eio.Stdenv.stdout env)
```

Setting up a project on OCaml 5.5 is three commands:

```bash
opam switch create 5.5.0
opam install eio_main utop
```

Concurrency primitives are structured, not ad hoc. `Fiber.fork` spawns inside a `Switch`, and the switch guarantees that when it exits, every child fiber has finished — no orphaned tasks holding a database connection:

```ocaml
let () =
  Eio_main.run @@ fun env ->
  Eio.Switch.run @@ fun sw ->
  List.iter (fun i ->
    Eio.Fiber.fork ~sw (fun () -> traceln "worker %d done" i))
    [1; 2; 3; 4]

(* Note: Fiber.fork expects ~sw with the correct type signature;
   the pattern above is the structural shape — see eio/examples/fiber for a buildable version. *)
```

The Linux backend rides on **io_uring**, which is a real performance advantage for high-throughput socket servers, and `Eio_mock` lets you test the same `main` function against fake flows and fake clocks with zero network. That mock-first design is the single best argument for Eio in a test-heavy codebase: **you can unit test I/O code without a mocking framework**, because the environment is an explicit parameter.

The cost: OCaml 5.2+ is mandatory, the API still moves between releases, and third-party bindings are thinner than Lwt's fifteen-year accumulation. If you are on OCaml 4.x, Eio is a rewrite, not an upgrade.

## Async — Jane Street's Scheduler, Priced With the Ecosystem

Async solves the same problem as Lwt and reaches nearly the same syntax — `let%bind` instead of `let%lwt` — but it is not a general-purpose community project. It exists to power Jane Street's trading stack, and it is designed to be used with `Core` (their stdlib replacement), `ppx_jane`, and the `Iron`/`Incremental` stack. Its README is candid about the trade-off:

> `Async` is a library for asynchronous programming, i.e., programming where some part of the program must wait for things that happen at times determined by some external entity (like a human or another program).

In practice that means a minimal Async program is written against `Command` and the scheduler loop:

```ocaml
open Core
open Async

let () =
  don't_wait_for (
    let%bind () = after (Time.Span.of_sec 1.) in
    print_endline "1 second elapsed";
    Shutdown.shutdown 0);
  never_returns (Scheduler.go ())
```

```bash
opam install core async
```

Async's debugging story is genuinely excellent — `Monitor.try_with`, backtraces across bind chains, and `Async_unix` error handling that will tell you *which* fiber broke — and its performance in low-latency, few-connection workloads is superb. But adopting Async means adopting Core. You will rewrite `Stdlib` idioms, and your library will be awkward for anyone outside the ecosystem. **If your team does not already write `Core`, Async is the most expensive of the three choices in 2026.**

## Dockerfile and Toolchain Setup for All Three

There is no official container for Lwt or Eio — they are libraries, not services. The reproducible pattern is the official `ocaml/opam` image on top of Debian, where each runtime is one `opam install` away:

```dockerfile
FROM ocaml/opam:debian-12-ocaml-5.2

# Lwt stack
RUN opam install -y lwt lwt_ppx

# Eio stack (OCaml 5.2+ required)
RUN opam install -y eio_main

# Async stack (choose this OR the two above)
# RUN opam install -y core async

WORKDIR /src
COPY . .
RUN opam exec -- dune build --profile release
CMD ["opam", "exec", "--", "dune", "exec", "./bin/main.exe"]
```

The `debian-12-ocaml-5.2` tag is the current stable base in the official repository. Pinning the OCaml version in the tag — rather than `opam switch create` inside the image — is what makes builds reproducible across developer machines and CI.

## Pitfalls and Migration Notes

**Blocking calls silently freeze the whole world.** In all three runtimes, a `Unix.sleep`, a synchronous `In_channel.input_all` on a slow socket, or a naive TCP client library will block the scheduler and stall every other fiber in the process. This is the number one production incident in OCaml async code. Audit every FFI boundary and thread it through the runtime's own IO layer.

**Mixing runtimes inside one process does not work.** `Lwt_main.run` cannot be nested inside `Eio_main.run`, and Async's `Scheduler.go` owns the process. Bridging is done at *process* boundaries — a gRPC call, a Unix socket, or a queue — not by calling two schedulers in one event loop. If you must migrate incrementally, put Lwt behind an HTTP or RPC boundary and let Eio own the new process.

**Eio's API is still stabilising.** Between minor releases you will hit renames in `Eio.Switch`, `Eio.Path`, and the backend selection modules. Pin exact versions in `dune-project` and upgrade deliberately — do not float on `latest` in production.

**`Lwt.pick` cancels losers, and cancellation is not a rollback.** A cancelled write may have already hit the disk. Any resource intended to survive a race must be committed before the race begins.

**Thread-safety is not free in any of them.** Lwt's cooperative model means no locks *by default*, not never; a `Lwt_preemptive.detach` callback touching shared `ref` state is a data race. Eio's domain pools have the same problem with `Atomic` versus `ref`: shared mutable state across domains needs real synchronisation.

**Async upgrades track Core.** A `Core` bump is a breaking-change event for the entire dependency tree. Budget for it.

## FAQ

**Is Eio fast enough for production in 2026?**
Yes. Its Linux backend uses `io_uring`, and it is the runtime the OCaml multicore developers build for. The risk is API churn, not throughput — pin versions and you are fine. For high-connection-count socket servers it is the fastest of the three on OCaml 5.

**Can I use Lwt and Eio together in one application?**
Not in one event loop. `Lwt_main.run` and `Eio_main.run` both want to own scheduling in the process. Run them in separate processes and connect them over a socket or RPC, or migrate whole services one at a time and keep the monad at the edges.

**Why does Async have far fewer stars than Lwt or Eio?**
Because its audience is deliberately narrow: it is maintained by Jane Street for teams already using `Core`. Popularity on GitHub measures general adoption, and Async is not marketed for general adoption. Fewer stars does not mean less ability — it means smaller addressable audience.

**Do I need to rewrite everything to move from Lwt to Eio?**
The type signatures change from `'a Lwt.t` to plain direct style, so yes, mechanical rewriting is required — but the rewriting is *deleting* `let%lwt` and `Lwt.return`, not redesigning logic. The hard part is not syntax; it is the third-party libraries that only ship Lwt bindings.

**Which runtime should a brand-new OCaml project choose today?**
Eio, unless you have a specific reason not to. It has no viral monad, real structured concurrency, the best testability story with `Eio_mock`, and it is where OCaml 5 development energy is going. Choose Lwt when the ecosystem demands it; choose Async when you already live in Jane Street's world.

If you are building the web layer on top of whichever runtime you pick, our [comparison of Dream, Opium, and Ocsigen](../2026-09-04-ocaml-web-frameworks-dream-opium-ocsigen-comparison/) shows which framework binds to which scheduler. For the lower-level picture of event loops across languages, see [async IO runtimes: libuv vs boost.asio vs Tokio](../2026-06-20-async-io-runtime-libraries-libuv-boost-asio-tokio/), and pair either stack with the [OCaml testing libraries guide](../2026-08-01-ocaml-testing-libraries-ounit-alcotest-qcheck/) before you depend on `Eio_mock` for coverage.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Lwt vs Eio vs Async in 2026: Which OCaml Concurrency Runtime Should You Actually Use?",
  "description": "A practical 2026 comparison of OCaml concurrency runtimes Lwt, Eio, and Async: multicore support, direct-style versus monadic code, io_uring performance, migration cost, and which one to pick for a new service.",
  "datePublished": "2026-09-12",
  "dateModified": "2026-09-12",
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
