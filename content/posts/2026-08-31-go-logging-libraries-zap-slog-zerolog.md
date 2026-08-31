---
title: "Go Logging in 2026: zap vs slog vs zerolog — Pick the Right Logger for Your Service"
date: "2026-08-31"
tags: ["golang", "logging", "developer-tools"]
draft: false
---

Your Go service's logging choice shows up in every production incident you will ever debug — but most teams pick a logger in the first hour of a greenfield project and never revisit it. The cost of the wrong choice is not features; it is performance (a hot-path logger that allocates per event can add real latency), it is interoperability (libraries that force a logging dependency on their consumers), and it is context (a logger that cannot carry a request ID through a call chain makes distributed debugging miserable). In 2026 the field has effectively settled on three options: `log/slog` from the standard library, Uber's zap, and rs/zerolog. Here is how they really compare.

## TL;DR: Quick Verdict

**Start with `log/slog`** if you are on Go 1.21+ and want zero dependencies, a standard `Handler` interface, and ecosystem interoperability — it is the boring, correct default for new services. **Use zap** when you need maximum throughput with strong typing and a mature API, especially in latency-sensitive paths. **Use zerolog** when you want the lowest allocations, elegant chained-event syntax, and first-class context propagation in cloud-native microservices. All three emit structured JSON; slog is the standard, zap is the performance benchmark, zerolog is the ergonomic speed demon. For a brand-new service with no legacy constraints, slog with a JSON handler is the recommendation; reach for zap or zerolog when benchmarks tell you to.

## Side-by-Side Comparison Table

| Feature | log/slog (stdlib) | zap | zerolog |
|---|---|---|---|
| GitHub stars | — (Go stdlib, Go 1.21+) | 24,646 | 12,494 |
| Last push | Ships with Go releases | 2026-08 | 2026-08 |
| License | BSD (stdlib) | MIT | MIT |
| JSON output | Built-in `JSONHandler` | Built-in (production config) | Built-in, zero-allocation |
| Typed fields | `slog.Int`, `slog.String`, `slog.Any` | `zap.Int`, `zap.String`, codegen | Chained methods: `.Int()`, `.Str()` |
| Zero-allocation fast path | Partial (typed attrs) | Yes | Yes |
| Context propagation | `slog.InfoContext(ctx, ...)` | Manual (no built-in ctx fields) | `log.Ctx(ctx)` + `zerolog.Ctx` |
| Handler abstraction | Yes (`slog.Handler`) | Via `zapslog` adapter | Via `zerolog/slog` adapter |
| Grouped/namespaced fields | Yes (`slog.Group`) | Yes (`zap.Namespace`) | Yes (`log.With().Str()...`) |
| Dynamic level switching | `slog.LevelVar` | `zap.AtomicLevel` | `zerolog.SetGlobalLevel` |
| Console pretty output | TextHandler | Development config | ConsoleWriter |
| Library author recommended | Yes | No (consumer must adopt zap) | No (unless zero-dep acceptable) |
| Migration from logrus | Manual | Manual (guide exists) | Official migration guide |

## Decision Matrix: Which Logger Should You Pick?

| Use Case | Recommended Logger | Why |
|---|---|---|
| New Go service, Go 1.21+, no external deps wanted | slog | Standard `Handler` interface, JSON out of the box, future-proof |
| Open-source library that others import | slog | Never force a logging dependency on consumers; they can plug any backend |
| Maximum throughput in a latency-sensitive hot path | zap | Reflection-free typed encoders, production-proven at scale |
| K8s/cloud-native service with request-scoped context | zerolog | `log.Ctx(ctx)` makes request-ID propagation trivial |
| Replacing logrus in an existing codebase | zerolog or zap | zerolog has an official migration guide; zap mirrors logrus ergonomics with SugaredLogger |
| Deeply nested event with many fields | zerolog | Chained builder syntax reads cleanly and allocates nothing |
| You need runtime level changes from config/env | Any | `LevelVar`, `AtomicLevel`, `SetGlobalLevel` all support it |
| Team that wants compiler-checked field types | zap | Typed fields catch typos at compile time |

## log/slog: The Standard Library Logger

`log/slog` landed in **Go 1.21** and became the de facto standard for structured logging in the ecosystem. Its design is a `Logger` that writes through a `Handler` interface, with built-in `TextHandler` and `JSONHandler`. Because it is in the standard library, libraries can log through slog without forcing a dependency on consumers — and consumers can route those logs through any backend by installing their own handler. That single property has made slog the default recommendation for anything that other people will import.

**Basic usage with JSON output:**

```go
package main

import (
    "log/slog"
    "os"
)

func main() {
    logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
        Level: slog.LevelInfo,
    }))
    slog.SetDefault(logger)

    slog.Info("user logged in",
        "user_id", 42,
        "ip", "10.0.0.1",
        "region", "eu-west-1",
    )
    // {"time":"2026-08-31T12:00:00Z","level":"INFO","msg":"user logged in",
    //  "user_id":42,"ip":"10.0.0.1","region":"eu-west-1"}
}
```

**Typed attributes for the allocation-free fast path:**

```go
slog.Info("order shipped",
    slog.Int("order_id", 12345),
    slog.String("status", "shipped"),
    slog.Duration("processing_time", 320*time.Millisecond),
    slog.Group("customer",
        slog.Int("id", 7),
        slog.String("tier", "gold"),
    ),
)
```

**Context-aware logging (the killer feature for request tracing):**

```go
func handleRequest(ctx context.Context, r *http.Request) {
    // TraceID flows through ctx; every slog call picks it up
    slog.InfoContext(ctx, "request started",
        "method", r.Method,
        "path", r.URL.Path,
    )
    // ... handler code ...
    slog.InfoContext(ctx, "request finished", "status", 200)
}
```

Because slog is the standard, you also get `slog.Handler` adapters for zap (`go.uber.org/zap/exp/zapslog`) and zerolog (`github.com/rs/zerolog/slog`), letting you standardize on slog calls while keeping a high-performance backend. For most new services, slog with a JSON handler is genuinely all you need.

## zap: The Performance Benchmark

Uber's zap (**24,646 stars**, last push August 2026) has been the performance king of Go logging for years. Its JSON encoder avoids reflection and allocation through a code-generated fast path for typed fields, and its benchmark suite famously claimed an order-of-magnitude advantage over older reflection-based loggers. In 2026 it remains the default choice for teams that have measured their logging overhead and need the absolute floor.

**Production configuration:**

```go
package main

import (
    "time"

    "go.uber.org/zap"
)

func main() {
    logger, _ := zap.NewProduction() // JSON, Info level, sampled
    defer logger.Sync()              // flush buffered output on exit

    logger.Info("user logged in",
        zap.Int("user_id", 42),
        zap.String("ip", "10.0.0.1"),
        zap.Duration("latency", 120*time.Millisecond),
        zap.Namespace("db"),
        zap.String("query", "SELECT * FROM orders WHERE id = ?"),
    )
}
```

**The two-API split — `Logger` vs `SugaredLogger`:**

```go
// Fast, typed, verbose — prefer in hot paths
logger.Info("order created",
    zap.Int64("order_id", 12345),
    zap.Float64("total", 99.95),
)

// Ergonomic, fmt-style — fine for startup/rare paths
sugar := logger.Sugar()
sugar.Infow("order created",
    "order_id", 12345,
    "total", 99.95,
)
sugar.Infof("order %d created", 12345)
```

zap's typed fields catch typos at compile time (`zap.Int` vs `zap.String`), and `AtomicLevel` gives you runtime level switching for on-call debugging. The trade-off is API surface: zap is the most verbose logger here, and its `Logger.Sync()` discipline (deferred flush) is a footgun people forget.

## zerolog: Zero-Allocation Chained Events

zerolog (**12,494 stars**, last push August 2026) takes a different design: a fluent, chained builder API that reads like prose and avoids reflection entirely. Every field is a method call (`log.Info().Str("k", "v").Msg("...")`), and the package proudly claims zero allocations in its hot path. It also ships the cleanest context story of the three — a request ID dropped into the context with `log.Ctx(ctx)` is automatically attached to every log event in that chain.

**Basic usage:**

```go
package main

import (
    "github.com/rs/zerolog"
    "github.com/rs/zerolog/log"
)

func main() {
    zerolog.TimeFieldFormat = zerolog.TimeFormatUnix
    log.Info().
        Int("user_id", 42).
        Str("ip", "10.0.0.1").
        Dur("latency", 120*time.Millisecond).
        Msg("user logged in")
}
```

**Context propagation — the standout feature:**

```go
func middleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        ctx := log.With().
            Str("trace_id", r.Header.Get("X-Trace-Id")).
            Str("path", r.URL.Path).
            Logger().WithContext(r.Context())
        next.ServeHTTP(w, r.WithContext(ctx))
    })
}

func handler(w http.ResponseWriter, r *http.Request) {
    // Automatically includes trace_id and path from ctx
    log.Ctx(r.Context()).Info().Msg("handling request")
}
```

**Console output for development:**

```go
log.Logger = log.Output(zerolog.ConsoleWriter{Out: os.Stderr})
```

For teams running many small services with a trace ID in every request header, zerolog's context system eliminates an entire class of "where did this log come from" debugging. The chained API also reads better in code review than either slog's attribute lists or zap's field calls.

## Migration and Coexistence Strategies

Moving an existing codebase is where logging decisions actually get made or deferred. The pragmatic playbook:

1. **Logrus → zerolog**: use zerolog's official migration guide; the biggest change is converting `log.WithField("k", "v")` to chained calls and dropping `log.Info("text")` in favor of `log.Info().Msg("text")`.
2. **Logrus → zap**: keep your existing `log.*` call sites working via zap's SugaredLogger (`sugar.Infof`) and migrate hot paths to the typed API over time.
3. **Anything → slog**: because slog is a `Handler` interface, you can wrap your existing backend (`zapslog`, `zerolog/slog`, or third-party handlers) and gradually convert call sites. `slog.SetDefault` makes the swap globally effective.
4. **Libraries must stay dependency-free**: if you publish a Go module, log through slog (or not at all). Your consumers' choice of backend then decides where library logs land, and nobody inherits an indirect dependency on zap or zerolog.
5. **Test-mode hygiene**: in tests, install a `slog.TextHandler` pointed at `io.Discard` (or a test buffer) via `slog.SetDefault` — this also silences the default logger's noisy `level=INFO` output during `go test`.

For the rest of your Go service stack, our [Go HTTP middleware libraries comparison](../2026-06-24-go-http-middleware-libraries-negroni-alice-gorilla-mux/) shows how logging middleware composes, and the [Go dependency injection containers guide](../2026-08-27-go-dependency-injection-wire-fx-dig-comparison/) covers wiring these decisions into larger applications.

## Logging Pitfalls That Bite Go Developers

1. **Forgetting `defer logger.Sync()` in zap.** zap buffers output; without `Sync()` you can lose the final log lines on a crash or fast exit. `logger.Sync()` returns an error that is usually safe to ignore — but call it.
2. **Debug logs silently invisible.** slog defaults to `Info` level, zerolog defaults to `Info`, and zap's production config is `Info` with sampling. Your `logger.Debug(...)` calls are no-ops until you set `LevelDebug` / `SetGlobalLevel` — a common cause of "I added logging and nothing appears."
3. **Mixing `log` and slog.** The stdlib `log` package and `slog` write through separate channels; `log.Println` output bypasses your structured pipeline entirely. Replace `log.` call sites or route them with `slog.SetDefault` + a `log` bridge (`slog.NewLogLogger`).
4. **Reflection on every event in slog.** `slog.Any("payload", hugeStruct)` serializes through reflection on the calling goroutine. Prefer typed attrs (`slog.Int`, `slog.String`) in hot paths and reserve `Any` for rare events.
5. **Context fields never propagate in zap.** zap has no built-in context field injection; if you want trace IDs on every event you must add them manually per call or use the experimental `zapslog` adapter. zerolog's `log.Ctx(ctx)` and slog's `InfoContext` handle this natively.
6. **Logging secrets into structured fields.** A `zap.String("token", r.Header.Get("Authorization"))` writes credentials to disk and into your log pipeline. Redact headers, truncate long payloads, and treat logs as production data.
7. **Sampling surprises.** zap's production config samples to 100 events/sec by default (100 same-level events per second, then every Nth). Under heavy traffic you will see *fewer* lines than you expect — that is sampling, not data loss. Adjust `SamplingConfig` or set `Development: true` when investigating.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Logging in 2026: zap vs slog vs zerolog — Pick the Right Logger for Your Service",
  "description": "Compare log/slog, Uber zap, and rs/zerolog for Go logging in 2026 with live GitHub stats, real code examples, performance trade-offs, migration strategies, and production pitfalls.",
  "datePublished": "2026-08-31",
  "dateModified": "2026-08-31",
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

**Should I use slog instead of zap in 2026?**
For a new service: yes, start with slog. It is in the standard library, has a clean `Handler` interface, and covers 90% of logging needs with zero dependencies. Switch to zap when you measure real allocation or latency pressure in hot paths — slog's typed attrs close much of the gap, but zap still wins extreme throughput benchmarks.

**Is zerolog faster than zap?**
They trade blows depending on the workload; both are far ahead of reflection-based loggers and both are effectively allocation-free on their fast paths. Community benchmarks typically show zerolog marginally ahead on simple events and zap competitive on complex ones. Measure on your own workload — the difference rarely exceeds single-digit percentages.

**How do I migrate from logrus?**
zerolog publishes an official migration guide and its chained API maps cleanly onto logrus's `WithField`. For zap, use SugaredLogger's `Infow`/`Infof` for near-drop-in replacement, then convert hot paths to typed fields. The hardest part is usually not the API — it is deciding what to do with logrus's `log.SetFormatter` calls and global hooks.

**Can libraries use zap or zerolog?**
They can, but they shouldn't. A library that imports zap forces every consumer to carry zap as a dependency and locks them into zap's configuration. Log through slog (or the standard `log` package) so consumers can choose their backend. Both zap and zerolog expose slog handlers if you want their power at the application layer.

**How do I change log level at runtime?**
slog: create a `slog.LevelVar`, point `HandlerOptions.Level` at it, and `Set` from config or an HTTP endpoint. zap: `zap.AtomicLevel` with `UnmarshalText` from config. zerolog: `zerolog.SetGlobalLevel(zerolog.DebugLevel)` — global, so wire it to env or config on startup.

**Do I need JSON logs in production?**
If you ship logs to any aggregator (Grafana Loki, Elasticsearch, Datadog, ClickHouse), JSON is the lowest-friction format — parsers and dashboards consume it directly. If logs only ever go to a file you grep by hand, `TextHandler` (slog) or `ConsoleWriter` (zerolog) is more readable. Many teams log JSON in prod and pretty-print in dev.

**Does slog support structured logging with JSON?**
Yes — `slog.NewJSONHandler(os.Stdout, nil)` emits JSON objects with `time`, `level`, `msg`, and any attributes. The `TextHandler` variant emits `key=value` lines. Both implement the same `slog.Handler` interface, so switching formats is a one-line change.

**Which logger is best for a CLI tool?**
A CLI tool rarely needs a full structured pipeline. slog's `TextHandler` with a `slog.LevelVar` (so `--verbose` can enable debug) is the sweet spot: standard library, no dependencies, and output that humans can read. Reserve zap/zerolog for long-running services with log shipping.

**How do I add request IDs to every log line with zap?**
zap has no built-in context field propagation. Options: (a) attach a `zap.Field` to the context yourself and merge it per call, (b) use a middleware that adds fields to a derived logger stored in the context, or (c) adopt the experimental `zapslog` handler and call slog with context. zerolog and slog handle this natively — a point in their favor for service-oriented code.

**Are zap and zerolog compatible with slog?**
Yes. zap ships `go.uber.org/zap/exp/zapslog` (a `slog.Handler` backed by zap) and zerolog ships `github.com/rs/zerolog/slog`. This lets you standardize call sites on slog while keeping zap/zerolog as the high-performance backend — useful for gradual migrations.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
