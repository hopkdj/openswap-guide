---
title: "Scala Logging Libraries in 2026: scribe vs Log4cats vs Scala Logging — Which Should You Use?"
date: "2026-09-05"
tags: ["scala", "logging", "jvm", "functional-programming", "developer-tools"]
draft: false
---

Every JVM developer inherits the same 20-year-old logging stack: SLF4J as the facade, Logback as the backend, and an XML file that everyone pastes from Stack Overflow without reading. It works — and it is also the layer where Scala projects quietly diverge. In 2026 the Scala ecosystem offers three serious alternatives to the default: **scribe (552 stars), Log4cats (416 stars), and Scala Logging (924 stars)** — and they are not interchangeable. One is a from-scratch, cross-platform logger with programmatic configuration. One brings referential transparency to logging for the cats-effect world. One is the pragmatic macro-powered SLF4J wrapper that most classic Scala shops actually run in production.

Pick based on your stack, not on stars: the three libraries serve *different language communities within Scala*. This guide compares them with code pulled from the official repositories and live GitHub data from September 2026.

## TL;DR — Which Scala Logging Library Should You Pick?

**If you live in cats-effect and care that logging is referentially transparent (no hidden side effects, testable like any other effect), use Log4cats** — it is the Typelevel-ecosystem standard (last push September 4, 2026). **If you want the fastest setup with zero config files and you also target Scala.js or Scala Native, use scribe** — it is built from scratch, configured programmatically, and cross-compiles everywhere (last push September 4, 2026). **If you run a classic JVM service on SLF4J/Logback and just want convenient, macro-optimized logging calls, use Scala Logging** — it is the boring, battle-tested default from Lightbend (924 stars, the most-starred of the three).

## scribe vs Log4cats vs Scala Logging: The 2026 Comparison

| Dimension | scribe | Log4cats | Scala Logging |
|---|---|---|---|
| GitHub stars | 552 | 416 | 924 |
| Last push | Sep 4, 2026 | Sep 4, 2026 | Jul 31, 2026 |
| License | MIT | Apache-2.0 | Apache-2.0 |
| Author/org | outr (Matt Hicks) | Typelevel | Lightbend |
| Current line | 3.19.x | 2.8.x | 3.9.x (4.0.0-RC1 in progress) |
| Philosophy | From-scratch logger, no SLF4J dependency | Pure FP, effect-cancellable logging | Convenient SLF4J wrapper |
| Underlying | Own engine (macros) | SLF4J or own backends | SLF4J + Logback |
| Scala 2.12/2.13/3 | Yes | Yes | Yes (3.x via recent releases) |
| Scala.js / Native | Yes (JS + Native) | No | No |
| Config files | No — programmatic only (files optional) | No | Yes (Logback XML/conf) |
| Async logging | Built-in | Via effect | Via Logback async appender |
| MDC support | Yes | Limited (effect-local via IOLocal) | Yes (SLF4J MDC) |
| Referential transparency | No (direct calls) | Yes (`Logger[F]` in `F`) | No (direct calls) |
| Interop with Java libs | scribe-slf4j bridge | slf4j backend | Native SLF4J |
| Learning curve | Low | High (FP concepts required) | Lowest |
| Best for | Greenfield, cross-platform, no-config | cats-effect / Typelevel stacks | Classic JVM services on Logback |

**Decision matrix — 10-second pick**

| Use case | Recommendation | Why |
|---|---|---|
| Existing JVM service on SLF4J/Logback, minimal change | Scala Logging | Drop-in wrapper; macro check-enabled idiom for free; keeps your logback.xml |
| cats-effect application (http4s, fs2, Doobie) | Log4cats | `Logger[F]` composes with effects; no unsafe `IO(logger.info(...))` wrapping |
| Scala.js or Scala Native project | scribe | Only one of the three that runs off-JVM |
| New service, tired of logback.xml and dependency chains | scribe | `scribe.info("...")` works with zero setup; config in Scala code |
| Appender pipelines, log rotation, custom writers | scribe | Built-in writer/appender model, all programmatic |
| You must feed a corporate ELK/Splunk pipeline via logback | Scala Logging or scribe-slf4j | Both can route through SLF4J backends into existing infra |
| Pure FP team that bans implicit side effects | Log4cats | Referential transparency is the whole point |

## Scala Logging — The Pragmatic Lightbend Standard

Scala Logging is the most conservative of the three, and that is exactly its appeal: it wraps SLF4J (the interface every Java library already speaks) and adds Scala ergonomics. Its README's promise is *"convenient and fast"* — convenient because you call log methods directly, fast because a Scala macro applies the *check-enabled idiom* automatically. Instead of writing:

```scala
if (logger.isDebugEnabled) logger.debug(s"Some $expensive message!")
```

you write:

```scala
logger.debug(s"Some $expensive message!")
```

and the macro generates the guarded version for you — so the expensive string interpolation never runs when debug is disabled. Setup is the familiar two-liner: add the dependency and a Logback backend:

```scala
libraryDependencies += "com.typesafe.scala-logging" %% "scala-logging" % "3.9.5"
libraryDependencies += "ch.qos.logback" % "logback-classic" % "1.5.18"
```

and create loggers from a name, a class, or the type itself:

```scala
import com.typesafe.scalalogging.Logger

val logger = Logger[MyService]   // runtime class via implicit ClassTag
logger.info("Service starting")
```

Because it is a thin layer over SLF4J, everything your operations team already knows applies: `logback.xml`, MDC, async appenders, JSON encoders, syslog, file rolling. The maintenance signal is healthy — Lightbend pushed in July 2026 and a **4.0.0-RC1 is in the tag list**, signaling modernization work ahead. The trade-offs: it only runs on the JVM, it inherits SLF4J's design (thread-local MDC, mutable state), and it does nothing for effect systems — your cats-effect code still ends up wrapping calls in `IO(...)` or `Sync[F].delay(...)`.

## Log4cats — Referentially Transparent Logging for the Typelevel Stack

Log4cats exists to answer one uncomfortable question: *how do you log from cats-effect code without breaking referential transparency?* The naive approach wraps every call in an effect:

```scala
IO(logger.info("Doing something!")) *> IO.println("Hello, World!")
```

which is verbose, easy to get wrong, and — more subtly — the `logger.info(...)` inside the `IO` still executes the SLF4J call as a side effect at *description* time unless you are careful. Log4cats (Apache-2.0, Typelevel) fixes the abstraction level: logging becomes an effect described inside `F`, cancellable and composable like any other:

```scala
import org.typelevel.log4cats.Logger
import org.typelevel.log4cats.slf4j.Slf4jLogger
import cats.effect.Sync

def safelyDoThings[F[_]: Sync]: F[Unit] = for {
  logger <- Slf4jLogger.create[F]
  _      <- logger.info("Logging at start of safelyDoThings")
  result <- Sync[F].delay(doWork()).onError {
              case e => logger.error(e)("Something went wrong")
            }
  _      <- logger.info("Logging at end")
} yield result
```

The `Logger[F]` algebra offers `info`, `warn`, `error`, `debug` — all returning `F[Unit]` — plus `Logger[F].info(...)` via the `Logger[F]` typeclass when you need to pass logging capability through generic code. That last point is the architectural payoff: you can thread a `Logger[F]` through your service layers as an explicit capability instead of grabbing a global logger, which makes your code honest about its dependencies and trivially mockable in tests. The ecosystem around it is exactly what you would expect from Typelevel: backends for SLF4J plus custom writers, and tight integration with cats-effect's `IOLocal` for effect-local context instead of thread-local MDC. The cost is that Log4cats assumes you have already bought into cats-effect — outside that world it is pointless complexity, and its learning curve is the steepest of the three (latest tag 2.8.0, very active).

## scribe — The From-Scratch, Cross-Platform Logger

scribe (MIT, by Matt Hicks / outr) is the contrarian option: instead of wrapping the Java logging stack, it was **built from the ground up for Scala** — JVM, Scala.js, and Scala Native — with no configuration files and no mandatory dependencies. Its README is blunt about why: every other Scala logging framework inherits SLF4J/Log4J/Logback's performance costs, dependency chains, and file-based configuration, and none of them support Scala.js or Scala Native at all.

The quick start is the entire pitch:

```scala
libraryDependencies += "com.outr" %% "scribe" % "3.19.0"

// in code:
scribe.info("Yes, it's that simple!")
```

No `logback.xml`, no logger factory, no backend dependency — logging works immediately, and configuration is ordinary Scala code. The design centers on **writers and appenders** that you compose programmatically — console, file with rotation, custom network writers — plus built-in async logging and MDC support. Because it uses Scala macros to capture class/method/line information at compile time, it avoids the expensive reflection-based caller lookup that most JVM loggers pay at runtime; the author's benchmarks claim the fastest JVM logger in its class, and the architecture genuinely eliminates several overheads the Java stack cannot.

For teams migrating from SLF4J-based ecosystems, scribe ships a `scribe-slf4j` bridge so libraries that log through SLF4J route into scribe's pipeline:

```scala
libraryDependencies += "com.outr" %% "scribe-slf4j" % "3.19.0"
```

The trade-offs are the mirror image of its strengths: no config files means ops teams used to tweaking `logback.xml` in production need a Scala recompile instead (or the optional file-config module); the ecosystem of Logback appenders (JSON encoders, cloud integrations) does not transfer; and for teams standardized on SLF4J/Logback everywhere else, introducing scribe means running *two* logging stacks during transition. At 552 stars it is the smallest community of the three — but it is the only one that follows your code to Scala.js and Native.

## Pitfalls, Migrations, and Performance Traps

1. **Do not mix SLF4J and scribe without the bridge.** If your dependencies log via SLF4J and your app logs via scribe, you get duplicate or missing logs unless you add `scribe-slf4j`. The same applies in reverse — never run two active backends pointed at the same output.
2. **Thread-local MDC is a lie in async code.** Classic SLF4J MDC propagates through thread pools unreliably; log lines from async pipelines land under the wrong request context. cats-effect teams should use Log4cats with `IOLocal`; scribe's async writer handles context internally — know which mechanism your stack uses before you debug a "missing" request ID.
3. **Macro logging is not magic.** Scala Logging's check-enabled idiom only helps when you interpolate *inside* the call: `logger.debug(s"value=$x")`. Building the string before the call (`val msg = s"value=$x"; logger.debug(msg)`) compiles the interpolation eagerly and loses the benefit.
4. **Referential transparency is a discipline, not a flag.** If you adopt Log4cats but then call `Slf4jLogger.getLogger[IO]` and `unsafeRunSync()` it in odd places, you have imported the impurity back. The value only appears when `Logger[F]` flows through your whole call graph.
5. **Version matrices bite.** All three cross-compile Scala 2.12/2.13/3, but check the artifact for *your* Scala version before upgrading — scribe publishes per-version artifacts (`scribe_2.13`, `scribe_3`), and scala-logging's 4.0.0-RC1 signals breaking changes on the way. Pin versions in CI and test logging output as part of your smoke tests.
6. **Async logging changes failure semantics.** scribe's async writer and Logback's async appender both trade guaranteed delivery for throughput: on hard crash, buffered lines can be lost. For audit-critical logs, use synchronous writes or a reliable queue — the [Java/cross-language logging comparison (spdlog/logrus/zerolog/serilog/winston/logback)](../2026-06-20-logging-libraries-spdlog-logrus-zerolog-serilog-winston-logback/) covers how other ecosystems solve the same trade-off.
7. **Choosing a logging library is downstream of choosing an effect system.** Log4cats only makes sense on cats-effect — if your project runs ZIO, check the [Scala effect systems comparison (cats-effect/ZIO/Monix)](../2026-09-03-scala-effect-systems-cats-effect-zio-monix-comparison/) first, then pick the logging that matches the winner. And whatever you choose, the [Scala HTTP client ecosystem (http4s/akka-http/sttp/zio-http)](../2026-07-25-scala-http-clients-http4s-akka-http-sttp-zio-http/) and [Scala testing frameworks (ScalaTest/specs2/utest)](../2026-07-06-scala-testing-frameworks-scalatest-specs2-utest/) articles show how the same ecosystem logic plays out in adjacent layers of your stack.

## How to Evaluate Logging for Your Project

Run a two-hour spike that includes: (1) structured JSON output to stdout, (2) a request-ID threaded through an async flow, (3) log rotation, and (4) a unit test asserting a warning was emitted. Score each library on setup time, how much the logging code *leaked* into your business logic, and whether the ops team could configure it without a developer. In our experience the verdicts are consistent: classic services on Logback stay on Scala Logging; Typelevel apps already have Log4cats; and greenfield or cross-platform projects find scribe's zero-config start the most liberating. Logging is infrastructure — the best choice is the one your team stops thinking about fastest.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Scala Logging Libraries in 2026: scribe vs Log4cats vs Scala Logging — Which Should You Use?",
  "description": "Compare scribe, Log4cats, and Scala Logging — the three serious Scala logging libraries of 2026 — with live GitHub stats, official code samples, feature and decision-matrix tables, migration pitfalls, and FAQs.",
  "datePublished": "2026-09-05",
  "dateModified": "2026-09-05",
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

**What is the difference between Scala Logging and plain SLF4J?**
Scala Logging is a thin, macro-powered wrapper around SLF4J: you get the same backend ecosystem (Logback etc.) but Scala-friendly calls like `logger.debug(s"...")` that compile to guarded check-enabled code, so expensive interpolations are skipped when the level is disabled.

**Is Log4cats only for cats-effect users?**
Yes — Log4cats is built on cats-effect's typeclasses (`Sync`, `IOLocal`) and its entire value proposition is referentially transparent logging inside `F[_]` effects. Outside the Typelevel ecosystem it adds complexity without benefit.

**Does scribe work with Scala.js and Scala Native?**
Yes, that is its defining feature: scribe cross-compiles to JVM, Scala.js, and Scala Native, making it the only one of the three that works off-JVM. It also runs on Scala 2.12, 2.13, and 3.

**Which Scala logging library is fastest?**
scribe claims the fastest JVM logger in its class, with design choices (no SLF4J indirection, compile-time caller capture, built-in async) that avoid the Java stack's known overheads. In practice, for most applications the logging framework is not the bottleneck — the check-enabled macro in Scala Logging and effect-composition in Log4cats matter more for correctness than raw throughput.

**Can I migrate from Logback to scribe without breaking my dependencies?**
Yes — scribe publishes `scribe-slf4j`, an SLF4J bridge that routes third-party SLF4J calls into scribe's pipeline. Add the bridge, switch your own code to scribe calls, and remove the Logback dependency once you have verified all output in staging.

**What is the current version situation in 2026?**
scribe is on the 3.19.x line; Log4cats' latest tag is 2.8.0; Scala Logging is on 3.9.x with a 4.0.0-RC1 in the repository — expect breaking changes when 4.0 stabilizes. All three are actively maintained as of September 2026.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
