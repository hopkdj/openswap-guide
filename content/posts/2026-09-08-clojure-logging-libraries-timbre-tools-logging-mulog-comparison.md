---
title: "Clojure Logging in 2026: Timbre vs tools.logging vs mulog"
date: "2026-09-08"
tags: ["clojure", "logging", "observability", "jvm", "developer-tools"]
draft: false
---

Logging is the last thing Clojure developers think about and the first thing they regret. Six months into a service, someone asks "what happened at 03:12 UTC?" and you discover your logs are a wall of half-formatted strings that no log aggregator can parse, or worse, nothing at all — because the logger you picked never wrote anywhere. Clojure's logging ecosystem has three serious answers, and they are not interchangeable: **Timbre (1,484 stars, EPL-1.0)** — the pure-Clojure batteries-included logger that is the community default; **tools.logging (409 stars, EPL-1.0)** — the official facade that delegates to Java logging backends, Clojure's answer to SLF4J; and **μ/log (539 stars, Apache-2.0, pronounced "mjuːlog", usually written mulog)** — an event-stream observability library that logs *data, not words*. Each one solves a different failure mode.

## TL;DR / Quick Verdict

If you want a logger that works the moment you add the dependency — Clojure and ClojureScript, no XML, no properties files, config as a plain map — use **Timbre**. If you are building a library that must coexist with a Java logging stack (Log4j2, Logback, SLF4J) or you want your Clojure code to write into an existing enterprise pipeline, use **tools.logging** — it has no output of its own and simply routes your calls to whichever backend is on the classpath. If your goal is *observability* — structured events flowing to Elasticsearch or a metrics store, with context propagation — use **μ/log** and stop formatting strings entirely. And note the 2026 status update: Timbre's author now recommends **Telemere** (a modern rewrite) for brand-new projects, while continuing to maintain Timbre with zero pressure on existing users.

## The Comparison Table

| Feature | Timbre | tools.logging | μ/log |
|---|---|---|---|
| Repository | ptaoussanis/timbre | clojure/tools.logging | brunobonacci/mulog |
| GitHub stars (2026-09-08) | **1,484** | 409 | 539 |
| License | EPL-1.0 | EPL-1.0 | Apache-2.0 |
| Latest release | v6.8.0 (2025-08-21) | 1.3.1 | 0.10.1 |
| Last push | 2025-11-06 | 2026-04-10 | 2026-06-27 |
| What it is | Full logging library | Facade over Java loggers | Event-stream / data logging |
| Own output sinks | Yes (console default, custom appenders) | **No — delegates to backend** | Via publishers (`:type :console`, Elasticsearch, etc.) |
| ClojureScript support | **Yes** | No (JVM only) | Yes |
| Configuration | Single `*config*` Clojure map | Backend-specific (out of scope) | Publishers + global/local context |
| Performance story | Fast, compile-time elision of disabled calls | Overhead of the chosen backend | **<300ns per event**, fully async processing |
| Structured data | Via custom appenders | No (message strings) | **Native — events are maps** |
| Context propagation | Middleware fns | No | `set-global-context!` + local context |
| Best for | Application defaults | Libraries & Java interop | Distributed-system observability |

## Decision Matrix

| Use case | Recommended tool | Why |
|---|---|---|
| New Clojure app, want logs today with zero ceremony | **Timbre** | Add dep, `(info "...")`, done. Config is a Clojure map, not XML |
| Writing a library others will depend on | **tools.logging** | Never force a logging backend on consumers; delegate at runtime |
| Migrating a Java service to Clojure, Log4j2 config already exists | **tools.logging** | Routes into the existing backend and its configuration |
| Microservices shipping events to Elasticsearch / metrics stores | **μ/log** | Events as data with publishers; no string parsing on the other end |
| ClojureScript frontend or GraalVM native image | **Timbre** (or μ/log) | Both support ClojureScript; Timbre runs in Graal tests |
| High-throughput request logging where `str` interpolation hurts | **μ/log** | Sub-300ns events, async rendering, memory-bounded |

## Timbre: The Community Default

Timbre's pitch, from its own README, is aimed at anyone who has configured Log4j: *"Getting even the simplest Java logging working can be maddeningly complex, and it often gets worse at scale as your needs become more sophisticated. Timbre offers an all Clojure/Script alternative that's fast, deeply flexible, easy to configure with pure Clojure data, and that just works out the box."* No XML, no properties files — a single dynamic `*config*` map controls everything.

Setup and basic use:

```clojure
;; deps.edn:  com.taoensso/timbre {:mvn/version "6.8.0"}

(ns my-ns
  (:require
    [taoensso.timbre :as timbre
      :refer [log trace debug info warn error fatal report spy]]))

(info "This will print")
;; => 15-Jun-13 19:18:33 localhost INFO [my-app.core] - This will print

(spy :info (* 5 4 3 2 1))  ;; logs the expression AND returns its value => 120

(trace "This won't print due to insufficient log level")
```

The architecture is deliberately simple — the README/wiki describes a logging call as six steps: consult the dynamic `*config*`; bail if the level is below the minimum; bail if the namespace is filtered; build a **log data map** containing all arguments; pass it through middleware functions `(fn [data]) -> ?data`; then hand it to every **appender function** `(fn [data]) -> ?effects`. Appenders are just functions, so "write to my database" or "send an alert" is ordinary Clojure:

```clojure
;; Levels: :trace < :debug < :info < :warn < :error < :fatal < :report
(timbre/set-min-level! :warn)         ; all namespaces
(timbre/set-ns-min-level! :debug)     ; current namespace only

;; Per-namespace minimums via pattern matching:
(timbre/set-config! {:min-level [[#"taoensso.*" :error]
                                 [#{ "*"} :debug]]})
```

For production, Timbre can even **elide disabled logging calls at compile time** — set `TAOENSSO_TIMBRE_MIN_LEVEL_EDN=':warn'` (or the equivalent JVM property) and lower-level call sites disappear from the compiled artifact entirely, which matters in ClojureScript bundles and GraalVM native images. Optional interop with tools.logging and SLF4J v2 is built in.

**The 2026 status update you need to know:** the README now opens with a note from Peter Taoussanis recommending that *new* users consider **Telemere** — *"essentially a modern rewrite of Timbre"* — while stating there is *"zero pressure for existing users of Timbre to migrate."* Timbre v6.8.0 shipped 2025-08-21 and the project remains maintained. If you are starting fresh in 2026, evaluate Telemere; if you already run Timbre, nothing is forcing you anywhere.

## tools.logging: The Official Facade

tools.logging lives in the clojure org and does one thing well: *"Logging macros which delegate to a specific logging implementation, selected at runtime when the clojure.tools.logging namespace is first loaded."* It has no appenders, no levels of its own, no output — it is a stable Clojure API over whichever Java logging framework happens to be on your classpath:

```clojure
;; deps.edn:  org.clojure/tools.logging {:mvn/version "1.3.1"}

(require '[clojure.tools.logging :as log])

(log/info "Order" order-id "shipped")
(log/debugf "Retry %d/%d for %s" attempt max url)
(log/error e "Payment failed")   ; first-arg exceptions get full stack traces
```

If no factory is pinned, the implementation is auto-detected by whichever of these loads first: **SLF4J, Apache Commons Logging, Log4j 2, Log4j, java.util.logging**. The README is candid that auto-detection is fragile — applications often pull in multiple logging implementations as transitive dependencies — and *strongly advises* pinning the factory explicitly:

```bash
# leiningen :jvm-opts or deps.edn :jvm-opts
-Dclojure.tools.logging.factory=clojure.tools.logging.impl/slf4j-factory
```

The current namespace automatically becomes the "logger name", which means your existing Log4j2/Logback configuration (per-logger levels, routing, patterns) applies to Clojure namespaces with zero extra work. Two utilities round out the API: `log-capture!` redirects Java's `System.out`/`System.err` writes into the logging system, and `with-logs` binds `*out*`/`*err*` to it — invaluable when a transitive Java library insists on `println`.

**The trade-off:** tools.logging inherits both the power and the configuration burden of your Java backend — and if no backend is present, calls silently do almost nothing. It is a contract, not a solution.

## μ/log: Log Events, Not Words

μ/log starts from a different premise. Its author's manifesto is worth quoting: *"In any significant project I worked in the last 15 years, logging text messages resulted in a large amount of strings which was hard to make sense of, thus mostly ignored. μ/log's idea is to replace the '3 Pillars of Observability' with a more fundamental concept: 'the event'."* Where Timbre and tools.logging format strings, μ/log emits structured maps — *"logs events and data, not words"* — at under **300 nanoseconds per event**, with all rendering happening asynchronously and memory usage bounded.

```clojure
;; deps.edn:  com.brunobonacci/mulog {:mvn/version "0.10.1"}

(ns your-ns
  (:require [com.brunobonacci.mulog :as μ]))
  ;; or, for ASCII traditionalists: (require '[com.brunobonacci.mulog :as u])

;; events are maps: event-name, then any key/value pairs
(μ/log ::hello :to "New World!")

;; start a publisher so events actually go somewhere (console during dev)
(μ/start-publisher! {:type :console})
;; => {:mulog/trace-id #mulog/flake "4VTBeu2scrIEMle9us8StnmvRrj9ThWP",
;;     :mulog/timestamp 1587500402972,
;;     :mulog/event-name :your-ns/hello,
;;     :mulog/namespace "your-ns",
;;     :to "New World!"}
```

Realistic events carry whatever dimensions you will want to query later:

```clojure
(μ/log ::user-logged :user-id "1234567" :remote-ip "1.2.3.4" :auth-method :password-login)

(μ/log ::http-request :path "/orders" :method :post
       :remote-ip "1.2.3.4" :http-status 201 :request-time 129)

(μ/log ::invalid-request :exception x :user-id "123456789" :items-requested 47)
```

Because events are data, no aggregator needs to parse your formatting conventions — the Elasticsearch publisher indexes fields directly. Context is a first-class concept: `set-global-context!` attaches process-wide dimensions (app name, version, environment, host) to every event, and a thread-local context injects per-request dimensions (request id, tenant) that every event inside the scope inherits. Processing is designed to **drop events rather than crash the process**, and adding publishers never slows down the logging call itself.

**The trade-off:** μ/log is a philosophy shift. Your existing grep-based debugging habits and your Java logging config do not apply; if your team lives on plain text logs piped through `tail`, the structured-event model demands new tooling (even a console publisher prints EDN-ish maps, not tidy lines).

## Pitfalls: Where Each Library Bites

1. **tools.logging with no backend is a silent black hole.** If the factory auto-detection finds nothing (or finds only an unexpected impl), your `(log/info ...)` calls vanish. Always pin `clojure.tools.logging.factory` and add a console/`java.util.logging` backend as the floor.
2. **Multiple Java loggers on the classpath.** A typical Spring-adjacent classpath carries SLF4J bindings *and* Log4j2 *and* JUL. tools.logging picks the first it can load — which may not be the one your ops team configures. This is the exact failure mode the README warns about; pin the factory and verify with one `(log/info "hello")` in staging.
3. **`ex-info` data maps disappear from logs.** When logging exceptions through Log4j2, the default `%xThrowable` pattern prints only the message. The tools.logging README shows the fix: use `%throwable` in the pattern so `clojure.lang.ExceptionInfo` data maps are included. If you use Timbre, exceptions as the first argument generate full stack traces automatically.
4. **String-building in hot paths.** `(log/info (str "order=" id " status=" status))` builds the string even when the level is disabled. Timbre mitigates this with compile-time elision for truly hot code; μ/log sidesteps it entirely by never building strings at all. If you log inside a per-request loop, measure before assuming the cost is free.
5. **Timbre's default output is console-only.** Out of the box you get `println`-style output at `:debug` and above. File, JSON, and remote sinks are appenders you must configure — the docs list a `spit`-style file appender as the common first addition, and the interop wiki covers routing Timbre into tools.logging or SLF4J v2 for existing pipelines.
6. **Namespace-as-logger-name caveats.** tools.logging passes your namespace as the logger name; backends that perform stack inspection instead of honoring it will print unhelpful internal frames — configure the backend to display the logger name it was given (documented in the tools.logging README).
7. **Do not mix philosophies blindly.** Running μ/log *and* Timbre *and* tools.logging in one app is sometimes justified (facade for libraries + event stream for your own domain + Timbre for CLJS), but each layer adds configuration surface. Decide per namespace, not per line.

## FAQ

### Is Timbre abandoned in 2026?

No. Timbre v6.8.0 shipped in August 2025 and the project is still maintained. What changed: the author now recommends **Telemere** — described as "essentially a modern rewrite of Timbre" — for brand-new projects, with "zero pressure" on existing users to migrate. Timbre remains the safest default for existing codebases; evaluate Telemere before starting something greenfield.

### tools.logging vs Timbre: which should a library use?

A library should use **tools.logging** (or nothing at all) — it never forces a backend or configuration on consumers. An application should use **Timbre** or **μ/log**, because it actually owns the output. Using Timbre inside a library forces every downstream user to accept Timbre's config model; the facade exists precisely to avoid that.

### Can Timbre write into tools.logging or SLF4J?

Yes. Timbre's wiki documents optional interop with tools.logging and with Java logging via SLF4J v2, so a Timbre-based app can feed an existing enterprise logging pipeline without rewriting call sites.

### What is the difference between μ/log and normal logging libraries?

Normal loggers produce formatted *messages*; μ/log produces structured *events* (maps with a name and arbitrary key/value dimensions) that are rendered asynchronously by pluggable publishers. The author's argument: text logs must be parsed to be useful, while events are indexable, aggregatable, and queryable as-is. If your team aggregates into Elasticsearch or similar, μ/log removes the parse step entirely.

### Does μ/log support ClojureScript?

Yes — like Timbre, μ/log supports ClojureScript, and its design goal of logging "events and data" carries over to browser contexts where string log lines are even less useful.

### Which logging levels do these libraries have?

Timbre defines `:trace < :debug < :info < :warn < :error < :fatal < :report`. tools.logging delegates to whatever levels the chosen Java backend supports (typically TRACE through FATAL, plus OFF). μ/log is level-agnostic by design — the event name and dimensions carry the meaning, so filtering happens on event names and attributes rather than a fixed level ladder.

### I need JSON logs for a log collector. What should I use?

μ/log is the native answer — its publishers emit structured events that map directly onto JSON documents, and it ships Elasticsearch and other publisher types. With Timbre, write a custom appender that serializes the log data map to JSON; with tools.logging, configure your Java backend's JSON layout. All three can produce JSON; only μ/log treats it as the default rather than a formatting exercise.

### How do Timbre's async logging and μ/log's async processing differ?

Timbre offers configurable async logging and rate limits as appender-level options within a traditional logger. μ/log makes asynchrony the architecture: every event is queued and rendered by publishers off the hot path, with bounded memory and a documented preference for dropping events over crashing the process — so logging cost is decoupled from request latency by design, not by configuration.

## Choosing Your Logging Future

If your Clojure journey is just starting, Timbre gives you working logs in one dependency — and Telemere is worth a look as its modern successor. If you ship libraries or sit inside a Java shop, tools.logging is the polite, interoperable contract. And if you are building distributed systems where logs are the primary source of truth, μ/log's event-first model will change how you debug — for the better. The three libraries are complementary enough that a serious stack often contains two: the facade for library code, and a real logger for the application's own voice. For the full context of Clojure services, see our [Clojure HTTP client comparison](../2026-09-07-clojure-http-clients-clj-http-httpkit-hato-comparison/), the [Ring vs Compojure vs Reitit web framework guide](../2026-08-29-ring-vs-compojure-vs-reitit-clojure-web-framework-comparison/), and the [Clojure testing frameworks comparison](../2026-09-06-clojure-testing-frameworks-clojure-test-kaocha-midje-comparison/) — the three pieces every production Clojure service needs around its logger.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Clojure Logging in 2026: Timbre vs tools.logging vs mulog",
  "description": "Compare the three Clojure logging approaches: Timbre (pure-Clojure batteries-included logger), tools.logging (official facade over Java backends), and mulog (event-stream data logging), with code examples, pitfalls, and the 2026 Telemere update.",
  "datePublished": "2026-09-08",
  "dateModified": "2026-09-08",
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
