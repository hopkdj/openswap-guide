---
title: "C# Logging Libraries in 2026: Serilog vs NLog vs log4net — Which One Should You Use?"
date: "2026-08-31"
tags: ["csharp", "logging", "dotnet", "developer-tools"]
draft: false
---

Logging is the first thing you throw together and the last thing you fix — until the night a production outage leaves you staring at an empty log file and no way to answer "what happened at 03:14?" In the .NET world you have three mature choices — Serilog, NLog, and Apache log4net — and picking the right one is not a religious debate: it changes how fast you can correlate failures, how much your log infrastructure costs, and how easy it is to add context to every event. This comparison uses live GitHub data and real configuration examples so you can decide in five minutes instead of five months.

## TL;DR: Quick Verdict

**Choose Serilog** if you are starting a new ASP.NET Core service and want first-class structured logging with the richest sink ecosystem — it is the community default and the natural fit for JSON pipelines. **Choose NLog** if you need rock-solid file rotation, rule-based routing across many targets, or a library that keeps working in exotic hosting scenarios with almost no ceremony. **Choose log4net** only for legacy codebases that already use it — it is in maintenance mode, has no native structured logging story, and there is no reason to adopt it for new code. Serilog for new projects, NLog for config-driven file logging at scale, log4net for "don't touch what works."

## Side-by-Side Comparison Table

| Feature | Serilog | NLog | log4net |
|---|---|---|---|
| GitHub stars | 8,034 | 6,545 | 934 |
| Last push | 2026-07 | 2026-08 | 2026-08 |
| License | Apache 2.0 | BSD-3-Clause | Apache 2.0 |
| Structured logging | Native (message templates) | Yes (`${event-properties}`) | No (conversion patterns only) |
| Configuration | Code-first, JSON via appsettings | XML config, code, JSON | XML config |
| Sinks / targets | 100+ sinks (Seq, Elasticsearch, Grafana Loki, Splunk, file, console) | 50+ targets (file, console, database, network) | Appenders (file, console, event log, SMTP, ADO.NET) |
| File rotation | Via `RollingInterval` | Full-featured archive/rotate | Rolling date/size appenders |
| ASP.NET Core integration | `Serilog.AspNetCore` | `NLog.Extensions.Logging` | `log4net.Extensions.Logging` |
| Async logging | Via sinks / `Serilog.Sinks.Async` | Built-in async target wrapper | Buffering appender |
| Dynamic log level changes | Yes (via `LoggingLevelSwitch`) | Yes (runtime config reload) | Yes (config reload) |
| Active development | Very active | Very active | Maintenance mode |
| Learning curve | Low | Medium | Low |

## Decision Matrix: Which Logger Should You Pick?

| Use Case | Recommended Library | Why |
|---|---|---|
| New ASP.NET Core web API / microservice | Serilog | Best `ILogger<T>` integration, structured events by default, huge sink ecosystem |
| JSON logs for a log-shipping pipeline (Elasticsearch, Loki, ClickHouse) | Serilog | Sinks emit structured JSON with zero extra code |
| File-based logging on Windows services or legacy hosts | NLog | Unbeatable file target: rotation, archiving, retention policies |
| Long-running desktop or console tool that must not crash on log failure | NLog | Exception-tolerant targets, async wrapper by default |
| Legacy .NET Framework app already on log4net | log4net | Zero-risk incremental improvements; don't rewrite working infrastructure |
| High-throughput event streaming (100k+ events/sec) | NLog | Built-in async target wrapper with batch size and queue limits |
| You only want the standard `ILogger<T>` and nothing custom | Any (via MEL) | All three plug into `Microsoft.Extensions.Logging`; pick by sink needs |

## Serilog: Structured Logging as the Default

Serilog (**8,034 stars**, last push July 2026) made structured logging mainstream in .NET. Instead of concatenating strings, you log *message templates* with named properties — `Log.Information("User {UserId} checked out cart {CartId}", userId, cartId)` — and the sink layer decides whether properties become JSON fields, columns, or text. That one shift turns your logs from grep-fodder into queryable structured data.

**Install:**

```bash
dotnet add package Serilog.AspNetCore
dotnet add package Serilog.Sinks.Console
dotnet add package Serilog.Sinks.File
```

**Bootstrap configuration (console or worker):**

```csharp
using Serilog;

Log.Logger = new LoggerConfiguration()
    .MinimumLevel.Information()
    .WriteTo.Console()
    .WriteTo.File("logs/app-.log",
        rollingInterval: RollingInterval.Day,
        retainedFileCountLimit: 14)
    .Enrich.WithProperty("Application", "OrderService")
    .Enrich.WithMachineName()
    .CreateLogger();

Log.Information("Application starting at {StartupTime}", DateTime.UtcNow);

try
{
    // run the app
}
catch (Exception ex)
{
    Log.Fatal(ex, "Application terminated unexpectedly");
}
finally
{
    Log.CloseAndFlush();
}
```

**ASP.NET Core — hook into the host builder:**

```csharp
var builder = WebApplication.CreateBuilder(args);
builder.Host.UseSerilog((context, config) =>
    config.ReadFrom.Configuration(context.Configuration)
          .Enrich.FromLogContext()
          .WriteTo.Console()
          .WriteTo.File("logs/app-.log",
              rollingInterval: RollingInterval.Day));
```

Your existing `ILogger<T>` calls immediately become structured events. The `FromLogContext()` enricher pulls the `TraceId`, `RequestId`, and scoped properties from ASP.NET Core into every log event — which is what makes end-to-end request correlation trivial.

Serilog's real superpower is the sink ecosystem: Seq for local inspection, Elasticsearch for full-text search, Grafana Loki for Prometheus-style log streams, Splunk for enterprise pipelines, and dozens of niche sinks. Whatever your observability stack, there is almost certainly a sink for it.

## NLog: The Configuration-Driven Workhorse

NLog (**6,545 stars**, last push August 2026) is the most configurable logger in this comparison. You declare *targets* (where logs go), *rules* (which loggers and levels route where), and *layouts* (how each event is formatted), typically in an `NLog.config` file that can be edited at runtime without recompiling.

**Install:**

```bash
dotnet add package NLog
```

**NLog.config — file rotation, console, and async in one file:**

```xml
<?xml version="1.0" encoding="utf-8" ?>
<nlog xmlns="http://www.nlog-project.org/schemas/NLog.xsd"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      internalLogLevel="Warn"
      throwExceptions="false">

  <targets async="true">
    <target name="file" xsi:type="File"
            fileName="${basedir}/logs/app-${shortdate}.log"
            layout="${longdate}|${level:uppercase=true}|${logger}|${message} ${exception:format=tostring}"
            archiveFileName="${basedir}/logs/archive/app-${shortdate}.{#####}.log"
            archiveAboveSize="104857600"
            archiveEvery="Day"
            maxArchiveFiles="30" />
    <target name="console" xsi:type="Console"
            layout="${longdate}|${level:uppercase=true}|${logger}|${message}" />
  </targets>

  <rules>
    <logger name="Microsoft.*" minlevel="Warn" writeTo="file" />
    <logger name="*" minlevel="Info" writeTo="console,file" />
  </rules>
</nlog>
```

**Usage in code:**

```csharp
using NLog;

private static readonly Logger logger = LogManager.GetCurrentClassLogger();

logger.Info("User {UserId} placed order {OrderId}", userId, orderId);
logger.Warn(ex, "Retry {RetryCount} failed for order {OrderId}", retryCount, orderId);
```

Note the `async="true"` attribute on `<targets>`: NLog buffers log events in a background queue with configurable `batchSize` and `overflowAction`, which keeps logging latency off the request thread even at high event rates. Its file target is the best in .NET — automatic archiving by size or time, retention limits, and crash-safe writes. For a Windows service or a legacy host where a `log.txt` file is the contract, NLog is the safest pick.

**ASP.NET Core integration:**

```csharp
var builder = WebApplication.CreateBuilder(args);
builder.Logging.ClearProviders();
builder.Logging.SetMinimumLevel(LogLevel.Information);
builder.Host.UseNLog(); // reads NLog.config automatically
```

## log4net: Legacy, Stable, and Mostly Frozen

Apache log4net (**934 stars**, last push August 2026) is the .NET port of the famous Java log4j. It popularized appenders, levels, and XML configuration, and it is embedded in an enormous amount of legacy .NET Framework code. The project is in maintenance mode: security fixes and compatibility updates, but no structural evolution. There is no native structured logging — you format text with conversion patterns like `%date [%thread] %-5level %logger - %message%newline`.

**Install:**

```bash
dotnet add package log4net
```

**log4net.config — rolling file appender:**

```xml
<?xml version="1.0" encoding="utf-8"?>
<log4net>
  <appender name="RollingFile" type="log4net.Appender.RollingFileAppender">
    <file value="logs/app.log" />
    <appendToFile value="true" />
    <rollingStyle value="Date" />
    <datePattern value="yyyyMMdd" />
    <maxSizeRollBackups value="30" />
    <layout type="log4net.Layout.PatternLayout">
      <conversionPattern value="%date [%thread] %-5level %logger - %message%newline" />
    </layout>
  </appender>
  <root>
    <level value="INFO" />
    <appender-ref ref="RollingFile" />
  </root>
</log4net>
```

**Usage — you must explicitly load the config:**

```csharp
using log4net;
using log4net.Config;

[assembly: XmlConfigurator(ConfigFile = "log4net.config")]

public class OrderProcessor
{
    private static readonly ILog log = LogManager.GetLogger(typeof(OrderProcessor));

    public void Process(Order order)
    {
        log.Info($"Processing order {order.Id}");
    }
}
```

The `[assembly: XmlConfigurator]` attribute is the step everyone forgets — without it, log4net silently logs nothing. In a .NET Core app you call `XmlConfigurator.Configure(new FileInfo("log4net.config"))` explicitly instead. If your codebase already runs on log4net and the log pipeline works, leave it alone; migration buys you structured logging but costs real effort across every logger call site. For the serialization side of your observability pipeline, our [C# serialization libraries comparison](../2026-07-05-csharp-serialization-libraries-newtonsoft-json-messagepack-protobuf-memorypack/) covers how to format the events you collect.

## Logging Pitfalls That Cost You Debugging Time

1. **String interpolation destroys structured logging.** With Serilog and NLog, `Log.Information($"User {id} logged in")` creates one undifferentiated string — the property is lost forever. Always use template syntax: `Log.Information("User {Id} logged in", id)`. This is the single most common structured-logging mistake.
2. **Forgetting to load the config.** log4net with no `XmlConfigurator` call logs nothing — no error, no file. NLog is more forgiving (it configures itself with sane defaults), but a misplaced `NLog.config` (wrong output directory, wrong `CopyToOutputDirectory` setting) produces the same silent void.
3. **Logging PII and secrets.** URLs, auth tokens, and personal data end up in plaintext files and then in your log-shipping pipeline. Set `MinimumLevel` deliberately, redact properties with enrichers, and treat logs as production data with retention policies.
4. **Synchronous logging under load.** The default file sink writes on the calling thread. Wrap NLog targets with `async="true"` or add `Serilog.Sinks.Async`; otherwise a slow disk (or a network sink like Seq) makes every log call a hidden latency tax on your request path.
5. **`Log.CloseAndFlush()` matters.** On shutdown, Serilog buffers events; without `CloseAndFlush()` in your `finally` block you lose the last few hundred events right when you need them most (crash reports!).
6. **Over-logging at `Information` in production.** Every `Log.Information` in a hot loop is a string allocation and an I/O event. Use `Debug`/`Trace` for verbose paths and let the config decide what ships to disk — that is exactly why NLog's rule engine and Serilog's `LoggingLevelSwitch` exist.
7. **Event IDs and scopes are free correlation.** With MEL, always log inside `using (logger.BeginScope(...))` for multi-step operations; the scope context flows into Serilog's `FromLogContext()` and NLog's `${mdlc}` — it turns "a log file" into "a timeline of one request." If you are building out a full .NET service, our [C# dependency injection containers guide](../2026-07-04-csharp-di-containers-autofac-ninject-castle-windsor-simpleinjector-lamar/) and [C# HTTP client libraries comparison](../2026-08-02-csharp-http-client-libraries-restsharp-refit-httpclientfactory/) cover the surrounding stack.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "C# Logging Libraries in 2026: Serilog vs NLog vs log4net — Which One Should You Use?",
  "description": "Compare Serilog, NLog, and Apache log4net for C# and .NET logging in 2026 with live GitHub stats, real configuration examples, structured logging guidance, and production pitfalls.",
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

**Which C# logging library is best for ASP.NET Core in 2026?**
Serilog is the most popular choice: `Serilog.AspNetCore` replaces the default MEL providers in one line, message templates give you structured events for free, and `FromLogContext()` enriches everything with `TraceId`. NLog is a strong second if you prefer XML-driven configuration. log4net works but adds no value over the built-in providers.

**Is log4net still maintained?**
Yes, but in maintenance mode. The Apache project pushed commits as recently as August 2026, mostly dependency and security updates. It is not dead — but it has no structured logging, no modern sink ecosystem, and no roadmap for either.

**Can NLog do structured logging?**
Yes. NLog supports `${event-properties}` in layouts, and when you log with message templates (`logger.Info("User {Id} logged in", id)`) the properties are captured. You can emit JSON with the `JsonLayout` target or the `NLog.Layouts.JsonLayout` class, so NLog works fine in JSON log pipelines too.

**Which is faster: Serilog or NLog?**
At typical application volumes (1–10k events/sec) both are far faster than any sink you will attach. Under extreme load, NLog's built-in async target wrapper with batching tends to win on throughput; Serilog's `Serilog.Sinks.Async` closes most of the gap. log4net is measurably slower, mostly due to per-event formatting.

**How do I migrate from log4net to Serilog?**
Mechanically it is simple: replace `LogManager.GetLogger` with `Log.GetLogger` or inject `ILogger<T>`, and translate appenders to sinks. The real work is auditing every `$"..."` interpolation to use message templates and deciding where PII needs redaction. For large codebases, do it incrementally — both can run side by side via MEL during the transition.

**Do I need Serilog if I only use `ILogger<T>`?**
The built-in `Microsoft.Extensions.Logging` providers are fine for simple console/file output. You reach for Serilog or NLog when you need structured properties, richer sinks (Seq, Elasticsearch, Loki), runtime level switching, or enrichers — the things MEL deliberately leaves to providers.

**Can I use Serilog and NLog in the same project?**
Technically yes, but don't. Both can plug into `Microsoft.Extensions.Logging` simultaneously, but you get two configuration systems, two sets of buffers, and confusing log output. Pick one provider per process.

**How do I log to multiple destinations with NLog?**
Define multiple targets and a rule that routes to several of them: `<logger name="*" minlevel="Info" writeTo="console,file" />`. NLog also supports fallback groups (try the first target, fall back on failure) which is handy for flaky network sinks.

**What is the best way to log JSON in Serilog?**
Use a JSON-formatted sink such as `Serilog.Formatting.Compact` (`WriteTo.Console(new CompactJsonFormatter())`) or the Elasticsearch/Loki sinks, which emit structured JSON automatically. Your pipeline can then parse events without regex.

**Does log4net support async logging?**
It has buffering appenders (`BufferingAppenderSkeleton` subclasses) and community async wrappers, but nothing as polished as NLog's `async="true"` target wrapper or Serilog's async sink. For high-throughput .NET Core services, prefer either of the other two.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
