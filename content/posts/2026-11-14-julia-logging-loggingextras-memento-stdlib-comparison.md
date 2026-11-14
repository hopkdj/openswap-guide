---
title: "Julia Logging in 2026: LoggingExtras.jl vs Memento.jl vs the Standard Library"
date: "2026-11-14"
tags: ["julia", "logging", "observability", "developer-tools"]
draft: false
cover: "/img/screenshots/julia-logging.jpg"
description: "A hands-on comparison of Julia's built-in Logging stdlib, LoggingExtras.jl and Memento.jl — routing, structured fields, file rotation and which one to pick in 2026."
---

# Julia Logging in 2026: LoggingExtras.jl vs Memento.jl vs the Standard Library

Your Julia service works fine in development and then, in production, you discover the logs are a single undifferentiated stream of `@info` lines going to stderr with no timestamps you control, no rotation, and no way to send warnings to a separate file. Julia 1.13.4 ships a logging system that is genuinely well designed — but its default configuration is deliberately minimal, and the ecosystem around it is smaller than in Python or Go. Picking the right layer now saves you a painful refactor later.

**TL;DR:** Use the **standard library** for scripts, notebooks and small services — it is already there, costs nothing, and `with_logger` covers 80% of needs. Reach for **LoggingExtras.jl** the moment you need two destinations, per-module filtering, or time-based file rotation; it is the de-facto production choice and composes cleanly with the stdlib. **Skip Memento.jl for new work** — its own README states it is largely unmaintained and the author has moved off Julia. Only adopt Memento if you are inheriting a codebase that already depends on it.

## The three options at a glance

| | stdlib `Logging` | LoggingExtras.jl | Memento.jl |
|---|---|---|---|
| Latest activity | Ships with Julia 1.13.4 | Last push 2026-07-13 | Last push 2026-06-11 |
| GitHub stars | n/a (core repo ~48k) | 157 | 88 |
| License | MIT | MIT | MIT |
| Composability | Manual (`with_logger`) | Full — tee, filter, transform | Hierarchical logger tree |
| Structured key=value fields | Yes (`@info "msg" k=v`) | Yes (inherits) | Yes, plus record dicts |
| Multiple sinks out of the box | No | Yes (`TeeLogger`) | Yes (handlers) |
| Per-module filtering | Only via `JULIA_DEBUG` | Yes (`EarlyFilteredLogger`) | Yes (`getlogger("Mod")`) |
| File rotation | No | Yes (`DatetimeRotatingFileLogger`) | No (handlers only) |
| Maintenance status | Active (core) | Active | **Self-declared unmaintained** |
| Learning curve | Low | Medium | Medium-high |

The maintenance row is the one that matters most in 2026. Memento's README opens with a warning that Invenia no longer exists and the maintainer no longer uses Julia. That is not a reason to panic-migrate a working system, but it is a decisive reason not to start a new one there.

## How Julia's logging actually works

Julia's logging is built around three functions that every logger must implement: `shouldlog`, `min_enabled_level`, and `handle_message`. Everything else — macros, filters, routing — is composition on top of that contract. This is why third-party packages integrate so cleanly: they are not competing with the stdlib, they are wrapping it.

```julia
using Logging

logger = ConsoleLogger(stderr, Logging.Info)
global_logger(logger)

@info "Config loaded" path = "/etc/app/config.toml" rows = 42
@warn "Cache miss" key = "session:91f2"
```

Two details surprise newcomers. First, `@info` supports structured key-value pairs, so you get machine-parsable fields without a JSON dependency. Second, the log level check happens at the macro boundary, which means the level is filtered before the message is formatted — relevant when your log payload involves string interpolation of large objects.

The standard library gives you `ConsoleLogger`, `SimpleLogger`, and `NullLogger`. `ConsoleLogger` handles colorized output, module prefixes, and multi-line messages; `NullLogger` swallows everything and is the correct tool in tests where you want silence. Filtering by module is possible without any package:

```bash
# Show debug output only for the Database and HTTP modules
JULIA_DEBUG=Database,HTTP julia --project=. src/main.jl
```

That environment variable is the escape hatch that saves many people from installing a package on day one. It is coarse — you cannot say "debug for Database, but only messages containing 'retry'" — but for a single-process script it is enough.

### Where the stdlib stops being enough

Three requirements push teams off the baseline. You want **warnings in one file and everything in another** — the stdlib has no fan-out. You want **rotation by date** because a long-running service will otherwise fill the disk. You want **per-module level overrides in code** rather than in an environment variable. Each of these is a two-line change with LoggingExtras and a small custom logger without it.

## LoggingExtras.jl — the composition layer

LoggingExtras adds nine loggers to the stdlib and, importantly, they all compose: any combination of them is itself a logger. The package documents a four-part taxonomy — sinks, filters, transformers, and a single tee — and that vocabulary is worth internalizing because it makes routing problems trivial.

```julia
using LoggingExtras

demux = TeeLogger(
    MinLevelLogger(FileLogger("info.log"; append = true), Logging.Info),
    MinLevelLogger(FileLogger("warn.log"; append = true), Logging.Warn),
)

with_logger(demux) do
    @info "normal operation"
    @warn "disk almost full"
    @debug "not written anywhere"
end
```

After this runs, `info.log` contains both entries and `warn.log` contains only the warning. No configuration file, no handler registration — just nested constructors that read top-to-bottom.

Time-based rotation is equally direct. The filename is a `DateFormat` string, and literal text must be escaped with backslashes so it is not interpreted as a date token:

```julia
using LoggingExtras

rotating = DatetimeRotatingFileLogger(
    pwd(),
    raw"\a\c\c\e\s\s-YYYY-mm-dd-HH-MM.\l\o\g",
)

with_logger(rotating) do
    @info "This lands in access-2026-11-14-20-05.log"
end
```

Every minute boundary opens a new file. If you need to compress or ship the closed file, pass a `rotation_callback` function and the package invokes it when the file rolls over.

The other workhorse is `EarlyFilteredLogger`, which filters on `level`, `module`, `group` and `id` before the message is processed:

```julia
using LoggingExtras

only_db_debug = EarlyFilteredLogger(current_logger()) do log
    log.level < Logging.Debug || log._module === Database
end
```

That single expression replaces a pile of `if` statements scattered through your code. For filtering on message *content* you need `ActiveFilteredLogger`, which receives the full log record and can drop messages by substring, regex, or rate.

Finally, `FormatLogger` is the right way to emit JSON lines without pulling in a logging framework. It takes a function that receives the IO stream and the log record, so you control the exact serialization:

```julia
using LoggingExtras

json_sink = FormatLogger(stderr) do io, log
    println(io, """{"level":"$(log.level)","msg":"$(log.message)","module":"$(log._module)"}""")
end

with_logger(json_sink) do
    @info "request handled" status = 200 latency_ms = 12
end
```

Two practical notes. `FileLogger` overwrites by default — pass `append = true` in any long-running service, or you will silently lose the previous run. And `TeeLogger` with several file sinks holds a file handle per sink, so do not construct one per request inside a web handler; build it once at startup and reuse it.

![Julia programming language logo](/img/screenshots/julia-logging.jpg "Julia — the language whose logging stdlib the packages here build on")

## Memento.jl — hierarchical loggers, frozen in time

Memento brings a Python-`logging`-style hierarchy to Julia: named loggers with inheritance, per-logger levels, and handlers attached to the tree. In principle that is a good model for a large application with many subsystems.

```julia
using Memento

logger = Memento.config!("info"; fmt = "[{level} | {name}]: {msg}")

info(logger, "Server started on port 8080")
warn(logger, "Connection pool exhausted")
setlevel!(logger, "debug")
```

Child loggers are obtained by name and inherit their parent's level and handlers, which means a single `setlevel!` on `Database` turns up verbosity for every database-related sub-logger at once. If you are porting a Python service and want the same mental model, that inheritance is genuinely convenient.

The problem is not the API — it is the trajectory. The repository has 88 stars, the last push was June 2026, and the README itself says the package is largely unmaintained and invites issues only for blocking problems. Nightly CI is often disabled. For a dependency that sits inside your error-reporting path, that is a real operational risk: logging libraries must keep pace with Julia's internals, and `handle_message` signatures have changed across minor releases.

There is a second, subtler cost. Memento's hierarchy duplicates a routing concept that LoggingExtras expresses compositionally. If you adopt Memento you also give up straightforward interoperability with packages that expect a stdlib `AbstractLogger` — you end up writing adapter code. Unless the hierarchy is a hard requirement, the composition model wins on both maintenance and interop.

## Performance and overhead: what to measure, not what to assume

Nobody should pick a logging library on vibes, but published micro-benchmarks for Julia logging are scarce and quickly stale. What you can do in five minutes is measure the two things that actually hurt: cost per disabled message, and cost per written message.

| Path | What dominates the cost | Practical guidance |
|---|---|---|
| Disabled `@debug` in hot loop | Level check at macro boundary | Keep the level check cheap; avoid closures that capture big state |
| `ConsoleLogger` to a terminal | Terminal I/O and color escape handling | Never log per-iteration to an attached TTY |
| `FileLogger` | `flush` per message (`always_flush = true` by default) | Set `always_flush = false` for throughput, but expect to lose the tail on a hard crash |
| `TeeLogger` with N sinks | N × sink cost, sequential | Two sinks fine, five sinks is an architectural smell |
| Memento named logger | Tree lookup plus format string parsing | Cache the logger in a `const` or a struct field, never per call |

A measurement harness that answers the question directly:

```julia
using Logging, LoggingExtras

function bench(logger, n = 100_000)
    elapsed = @elapsed with_logger(logger) do
        for i in 1:n
            @info "tick" i = i
        end
    end
    println(typeof(logger), ": ", round(elapsed / n * 1e9, digits = 1), " ns/msg")
end

bench(NullLogger())
bench(MinLevelLogger(NullLogger(), Logging.Warn))   # everything filtered
bench(FileLogger("/tmp/bench.log"; always_flush = false))
```

The `NullLogger` baseline tells you the framework overhead; the second line tells you the cost of a filtered message; the third is your realistic write path. If the filtered case is not dramatically cheaper than the written case, your expensive work is happening before the level check and belongs inside a `if min_enabled_level(logger) <= Logging.Debug` guard.

## Migration and coexistence notes

**Leave `println` behind gradually.** A mixed codebase is normal. Wrap the old stderr stream as one sink in a `TeeLogger` and migrate module by module; nothing breaks in between.

**Do not put a logger in a global mutable variable.** `global_logger()` is process-wide and inherited by tasks, but tests that set it leak state across test files. Prefer `with_logger(...) do ... end` inside the test, which is scoped and automatic.

**`@debug` is off by default and there is no built-in runtime toggle.** Julia discards debug messages unless `JULIA_DEBUG` names the module or the logger's minimum level is lowered. Teams frequently log at `@info` "temporarily" because they cannot flip debug at runtime — then forget to downgrade it. Set the level once in your startup code and leave the call sites alone.

**Rotation without retention is a disk leak.** `DatetimeRotatingFileLogger` opens new files forever. Pair it with the `rotation_callback` hook to gzip and delete files older than N days, or you have replaced one disk problem with another.

**Structured fields beat string concatenation.** `@info "request" status=200 ms=12` is searchable; `@info "request status=200"` is not. Retrofitting this later means touching every call site, so adopt the key-value form from day one.

## FAQ

### Is LoggingExtras.jl a replacement for Julia's Logging standard library?

No — it is an extension. LoggingExtras re-exports the stdlib and adds sinks, filters, and transformers that all subtype `AbstractLogger`. You still call `@info`, `@warn`, and `with_logger` exactly as before. The package is additive, which is why adopting it does not require rewriting existing call sites.

### Should I use Memento.jl for a new Julia project in 2026?

Generally no. Its README states the package is largely unmaintained, and the last push was June 2026 with no active maintainer. If you need named, hierarchical loggers, you can approximate them with `EarlyFilteredLogger` from LoggingExtras on the module field. Choose Memento only when inheriting an existing codebase that already depends on it.

### How do I write logs to two files with different levels in Julia?

Nest constructors: `TeeLogger(MinLevelLogger(FileLogger("info.log"; append = true), Logging.Info), MinLevelLogger(FileLogger("warn.log"; append = true), Logging.Warn))`. Wrap the block in `with_logger(...) do ... end`. Each sink applies its own level filter, so a warning appears in both files and an info message appears only in the first.

### How do I enable debug logging for one module only?

Set the `JULIA_DEBUG` environment variable to a comma-separated list of module names, for example `JULIA_DEBUG=Database,HTTP julia --project=. src/main.jl`. With LoggingExtras you can do the same in code using `EarlyFilteredLogger`, which filters on `log._module` and lets you combine module and level conditions in one predicate.

### Does Julia logging support JSON output?

Not out of the box, but `FormatLogger` from LoggingExtras makes it a three-line function: pass a closure that receives the IO stream and log record, then `println` a serialized object. Keep the schema stable and flat so downstream collectors can index `level`, `message`, and your key-value fields without custom parsing.

### What is the performance cost of logging in a hot loop?

Measure it rather than guessing: run the same loop against `NullLogger`, a fully filtered logger, and your real file sink. Filtering happens at the macro boundary, so disabled messages are cheap — but any string building you do *before* the macro call is not, and that is the usual culprit when teams report that logging "slowed everything down".

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Julia Logging in 2026: LoggingExtras.jl vs Memento.jl vs the Standard Library",
  "description": "Hands-on comparison of Julia's built-in Logging stdlib, LoggingExtras.jl and Memento.jl covering log routing, structured fields, file rotation, maintenance status and performance measurement.",
  "datePublished": "2026-11-14",
  "dateModified": "2026-11-14",
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

For related reading, see our [Julia web frameworks comparison](../2026-09-04-julia-web-frameworks-genie-oxygen-httpjl-comparison/) and the [Julia testing packages guide](../2026-10-20-julia-testing-test-retest-testitemrunner-comparison/). If you are still setting up tooling, the [Julia development toolchain review](../2026-09-13-julia-development-toolchain-juliaup-pkg-revise-comparison/) covers `juliaup`, Pkg and Revise.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
