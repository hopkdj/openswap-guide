---
title: "Nim Logging in 2026: std/logging vs Chronicles vs morelogging — Pick Right Before Your Logs Lie to You"
date: "2026-11-16"
tags: ["nim", "logging", "observability", "developer-tools", "comparison"]
draft: false
cover: "/img/screenshots/nim-chronicles-json-logs.jpg"
---

Most Nim services start with three lines: `import std/logging`, `addHandler(newConsoleLogger())`, `info "started"`. That is genuinely fine — until the service is in production, someone asks "which request produced this error?", and your log line says only `error: failed`. No request id, no customer, no duration. Adding structured fields later means touching every call site, because the standard library's logging procs accept **plain strings, not key-value pairs**.

Nim has three credible answers to this: the **standard library's `std/logging`**, **Chronicles** (the structured logging library that Status uses to ship Nimbus), and **morelogging** (a small file-rotation-focused library with journald support). They solve different problems at different layers, and the wrong choice shows up months later as either an unqueryable log pile or a compile-time configuration nightmare.

## TL;DR — Quick Verdict

**Use `std/logging`** for small tools, CLIs, and anything where a human reads the log. Zero dependencies, rotation built in since Nim 1.4. **Use Chronicles** for any long-running service you intend to operate — it is the only one of the three with true structured records (JSON sink), compile-time stripping of disabled log levels, and per-topic runtime filtering. **Use morelogging** only when what you actually need is non-blocking file writes with rotation, compression, and `journald` integration — and only after you check its LGPLv3 license against your distribution model.

If you are building a service that will run for years: **Chronicles, and accept the compile flags.** If you are writing a 200-line CLI: **std/logging, and stop reading.**

## Side-by-Side Comparison

| Criterion | std/logging | Chronicles | morelogging |
|---|---|---|---|
| Stars | 18,312 (`nim-lang/Nim`, last push 2026-11-15) | 177 (`status-im/nim-chronicles`, 2026-10-19) | 51 (`FedericoCeratto/nim-morelogging`, 2023-05-07) |
| License | MIT (Nim stdlib) | Apache-2.0 / MIT dual | LGPLv3 |
| Install | none (`import std/logging`) | `nimble install chronicles` | `nimble install morelogging` |
| Structured fields | No — variadic strings only | Yes — `info "event", key = value` | Partial (journald key-value pairs only) |
| Output formats | Text prefix via `fmtStr` | textlines, textblocks, JSON | Plain text templates |
| Sinks | console, file, rolling file | stdout, file, syslog, custom sinks | file, rotating file, journald |
| Rotation | Yes (`newRollingFileLogger`, line-based) | No built-in | Yes, time-based + gzip compression |
| Async / non-blocking | No (buffered writes) | Async-friendly (chronos ecosystem) | Yes — buffered async and threaded loggers |
| Level filtering | Logger `levelThreshold` + `setLogFilter` | Compile-time **and** runtime per topic | `level_threshold` per logger |
| Compile-time stripping | No | Yes — dead log code is erased | No |
| Project status | Actively maintained | Actively maintained | Beta, last commit 2023 |

## Decision Matrix: Pick in 10 Seconds

| Your situation | Recommended tool | Why |
|---|---|---|
| CLI tool or one-shot script | std/logging | Nothing to install, output stays readable |
| Long-running containerized service | Chronicles | JSON sink feeds Loki/Elasticsearch directly |
| Need request-scoped fields (trace id, user) | Chronicles | `logScope` attaches properties to every line |
| Log files must rotate daily and compress | morelogging | Built-in rotation with gzip, non-blocking writes |
| Shipping to systemd/journald | morelogging | `newJournaldLogger()` with structured keys |
| Hard requirement: zero dependencies | std/logging | Stdlib only |
| Need debug logs in prod without rebuild | Chronicles | `-d:chronicles_runtime_filtering:on` |
| Distributing a statically linked binary | Chronicles or std/logging | Avoids LGPLv3 relinking obligations |

## 1. std/logging — Boring, Correct, Limitless Strings

The stdlib module is handler-based: create loggers, register them, then call level templates. Its format variables are limited and documented — `$date`, `$time`, `$levelname`, `$levelid`, `$appname`.

```nim
import std/logging

var consoleLog = newConsoleLogger(
  levelThreshold = lvlInfo,
  fmtStr = "$date $time $levelname "
)
var fileLog = newFileLogger("logs/errors.log", levelThreshold = lvlError)
var rollingLog = newRollingFileLogger(
  filename = "logs/app.log",
  levelThreshold = lvlInfo,
  fmtStr = "$date $time $levelname ",
  maxLines = 100_000
)

addHandler(consoleLog)
addHandler(fileLog)
addHandler(rollingLog)

info "server listening on ", 8080
error "upstream failed: ", "dial tcp 10.0.0.5:5432"
```

Note what happened on the last two lines: `info` takes `varargs[string]` and concatenates. There is no `key = value` form. To get structure you format strings yourself:

```nim
proc logRequest(reqId, path: string, ms: int) =
  info "req=", reqId, " path=", path, " ms=", ms
```

That works, and logfmt-ish output is parseable — but every consumer now depends on your ad-hoc key ordering and quoting. A path containing a space silently corrupts the parse. This is the boundary of what stdlib logging can do, and it is why Chronicles exists.

Two operational details worth knowing. **Buffers flush only on error and fatal by default** — for console and file loggers, set `flushThreshold` when constructing if you need info lines to appear immediately. And `setLogFilter(lvlInfo)` is process-global while `levelThreshold` is per logger; confusing the two produces "why is my debug logger silent" bug reports.

Where stdlib logging genuinely shines: `newRollingFileLogger` rotates on line count (`maxLines`, default 1,000), which is the right primitive on constrained hosts where disk fills faster than the day rolls over.

## 2. Chronicles — The Only Option With Real Structured Records

Chronicles inverts the model. A log statement is an **event with properties**, not a formatted string:

```nim
import chronicles

proc processOrder*(id: string, items: int) =
  logScope:
    requestId = id
    component = "orders"

  info "order received", items = items
  debug "validating", itemCount = items
```

Everything logged inside that scope carries `requestId` and `component` automatically, and the sink decides the wire format. The default `textlines` output looks like this:

![Chronicles textlines output](/img/screenshots/nim-chronicles-textlines-logs.jpg "Chronicles textlines sink — human-readable logfmt output")

Switch to the JSON sink and the same statements become queryable records:

![Chronicles JSON output](/img/screenshots/nim-chronicles-json-logs.jpg "Chronicles JSON sink — one JSON object per log event")

Configuration happens at compile time via `-d:` flags, which is both the library's superpower and its main trap:

```bash
# JSON records to stdout (containers, Loki, Elasticsearch)
nim c -d:chronicles_sinks=json src/app.nim

# JSON to a file, plus human-readable on stdout
nim c -d:chronicles_sinks="json[file],textblocks[stdout]" src/app.nim

# Strip all log statements below WARN from the binary entirely
nim c -d:release -d:chronicles_log_level=WARN src/app.nim

# Keep a debug level in the binary but switch it at runtime
nim c -d:chronicles_runtime_filtering:on src/app.nim

# Per-topic levels at compile time
nim c -d:chronicles_enabled_topics:orders:DEBUG,db:WARN src/app.nim
```

Runtime filtering, once enabled, is controlled with `setLogLevel`, `setLogEnabled`, and `setTopicState`. Sinks support absolute paths — `textblocks[stdout,file(/var/log/myapp.log)]` — and custom sinks can be plugged into `chronicles_sinks`.

The trap: **configuration placed in a build script is invisible to whoever runs the service.** If your Dockerfile compiles with `-d:chronicles_sinks=json` but a colleague builds locally without it, you get two different log formats from the same commit. Put those flags in `nim.cfg` or a `config.nims` committed to the repo, so every build path agrees.

Chronicles has no built-in rotation. In containers that is correct — you write to stdout and let the runtime handle it. On a bare-metal host you pipe through `logrotate` or accept unbounded files.

## 3. morelogging — Rotation, Compression, and journald

morelogging occupies a different niche: it is uninterested in structured logging (it is still on the roadmap) and very interested in not blocking your application while writing to disk.

```nim
import morelogging

let log = newAsyncFileLogger(
  filename_tpl = "$appname.$y$MM$dd.log",
  fmtStr = "$datetime $levelname ",
  level_threshold = lvlAll,
  writeout_interval_ms = 100,
  buffer_size = 1_048_576
)

log.info("started")
log.error("disk pressure")
```

For a daily-rotated, gzip-compressed archive, use the rotating threaded logger:

```nim
let rot = newThreadRotatingFileLogger(
  compress = true,
  filename_tpl = "/var/log/myapp/$appname.$y$MM$dd.log",
  rotate_interval = "1d",
  level_threshold = lvlInfo
)
rot.info("rotated write")
```

And on systemd hosts, the journald logger is the one I would actually pick — it writes native structured entries, and auto-adds `CODE_FILE`, `CODE_FUNC`, and `CODE_LINE`:

```nim
# compile with: nim c -d:systemd src/app.nim
let jlog = newJournaldLogger()
jlog.info("hello world", {"key_1": "value_1"})
```

Two caveats. The license is **LGPLv3**, which matters if you statically link the library into a proprietary binary — that is a legal question, not a technical one, so check it before shipping. And the repository's last commit was 2023-05-07 with the README declaring a beta status; it works, but you are adopting an unmaintained dependency. For a logging layer that every service depends on, that is a real operational risk.

## Pitfalls and Operational Notes

**Release builds silently eat your debug logs.** In `std/logging` the default compile behavior keeps everything, but Chronicles sets the level based on build type — debug in debug builds, info in release. Compile the level you actually want, and verify by searching the binary for a known debug string.

**Never log PII into a JSON sink without a filter.** Structured logging makes accidental data collection easier: `info "login", email = user.email` is one keystroke and now your email addresses live in Loki with a 30-day retention. Decide which fields are allowed in logs before you adopt the JSON sink, not after.

**`$appname`-style templates are not shell variables.** In morelogging, `filename_tpl = "$app.foo.log"` is expanded by the library; on the command line your shell may expand it first. Quote the argument in scripts.

**Rotation without size limits is not rotation.** Line-based (`std/logging`) and time-based (morelogging) rotation both ignore bytes written per line. A single 40 KB stack trace per error can blow past any disk budget. Cap line length or rotate on size where the workload is unpredictable.

**Async loggers can lose the tail.** Buffered writers drop the last buffer on `SIGKILL`. If a crash's final lines matter, flush on `SIGTERM` and keep error/fatal writes unbuffered.

**Containerized deployments should not rotate at all.** Write JSON to stdout, let the platform collect it. Running your own rotation inside a container just hides logs from the operator. The right pairing is **Chronicles JSON sink → stdout**, and morelogging reserved for bare-metal services.

For adjacent reading, see our [Nim toolchain comparison](../2026-10-25-nim-toolchain-nimble-choosenim-atlas-comparison/) and the [Nim async I/O guide](../2026-10-29-nim-async-io-chronos-asyncdispatch-threadpool/) — if you adopt Chronicles you will likely adopt chronos too. Our [Nim JSON serialization comparison](../2026-11-15-nim-json-serialization-stdlib-jsony-nim-serialization/) covers the data layer that makes structured logs actually consumable.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Nim Logging in 2026: std/logging vs Chronicles vs morelogging",
  "description": "Comparison of Nim logging libraries: the standard library's std/logging, Chronicles structured logging with JSON sinks, and morelogging with rotation, compression and journald support.",
  "datePublished": "2026-11-16",
  "dateModified": "2026-11-16",
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

**Does Nim's standard library support structured logging with key-value pairs?**
No. `std/logging` templates such as `info` and `error` accept `varargs[string]` and concatenate them, so structure must be encoded by hand (`info "req=", id`). For real key-value records you need Chronicles, which accepts `info "event", key = value` and `logScope` blocks.

**Why is Chronicles configured with compiler flags instead of a config file?**
Because the flags also drive dead-code elimination: `-d:chronicles_log_level=WARN` removes lower-level log statements from the compiled binary entirely, which removes both runtime cost and the risk of leaking sensitive values. The price is that build configuration matters — commit your flags in `nim.cfg` or `config.nims` so every build produces the same format.

**Can I get the log level to change at runtime without a rebuild?**
Yes, with Chronicles: compile with `-d:chronicles_runtime_filtering:on`, then call `setLogLevel`, `setLogEnabled`, or `setTopicState` at startup (typically from an environment variable). Keep in mind runtime filtering can only select among levels that survived compilation — a level stripped by `chronicles_log_level` cannot be re-enabled.

**Is morelogging safe for production use?**
It is functional and does what it claims (async buffered writes, daily rotation, compression, journald), but it is self-described as beta and its last commit was in May 2023. For a logging layer that every service depends on, that maintenance risk should be an explicit decision. Its LGPLv3 license also needs review if you link it statically into a closed-source binary.

**How do I ship Nim logs to Loki or Elasticsearch?**
Use Chronicles with the JSON sink on stdout (`-d:chronicles_sinks=json`) and let your container runtime collect it. One JSON object per event maps directly onto label-based ingestion without any parsing rules — no regex, no multiline stitching.

**Which option handles log rotation best on a bare-metal server?**
morelogging, by design: `newThreadRotatingFileLogger` rotates on an interval, can gzip the rotated file, and writes without blocking the caller. `std/logging`'s `newRollingFileLogger` rotates by line count and does not compress. Chronicles has no rotation and expects you to use `logrotate` or platform collection.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
