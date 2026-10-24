---
title: "Perl Logging in 2026: Log::Log4perl vs Log::Dispatch vs Log::Any — Stop Guessing"
date: "2026-10-25"
tags: ["perl", "logging", "developer-tools", "observability", "cpan"]
draft: false
---

Your Perl service has been running for nine years. It writes to three different log files because three different developers added logging in three different eras, one of them calls `print STDERR` inside a `unless $quiet` block, and nobody can turn on debug output for a single module without restarting everything. Every Perl shop has this file.

The three modules that fix it are **Log::Log4perl** (114★, pushed 2026-08-14), **Log::Dispatch** (12★, 2026-08-04), and **Log::Any** (14★, 2026-04-25). Ignore the star counts — these are CPAN modules, not GitHub projects, and their real install base is measured in reverse dependencies and decade-long production runs. Picking wrong means either a config-file culture war or a rewrite when you change log sinks.

## TL;DR: The 30-Second Verdict

- **Pick Log::Log4perl** when you want configuration outside the code: one `.conf` file, per-package log levels, hot reload on `SIGHUP`, zero code changes to add a syslog appender.
- **Pick Log::Dispatch** when you are writing a library or an application that wants to construct its sinks in Perl code, with no config file format to learn. It is the engine Log4perl sits on top of.
- **Pick Log::Any** when you maintain CPAN modules or a large in-house library tree and cannot impose a logging framework on your users. Logging becomes a no-op by default and the *application* chooses the backend.
- **Do not use all three.** Log4perl already embeds Log::Dispatch as its appender layer, and Log::Any can adapt to either — chain them deliberately or you get duplicate lines.

## What Each One Actually Is

These modules are not three competitors at the same layer. Understanding the layering removes most of the confusion:

**Log::Dispatch** is the lowest layer: a dispatcher holding a list of outputs (Screen, File, FileRotate, Syslog, Slack, whatever), each with a minimum level and a formatter callback. You configure it with Perl data structures.

**Log::Log4perl** is a full framework modeled on log4j: categories, levels, appenders, layouts, and — critically — an external configuration file. Its appenders *are* `Log::Dispatch::Output` subclasses, which is why the two feel similar.

**Log::Any** is not a logger at all. It is a facade: your code calls `$log->info(...)` on a proxy, and an *adapter* decides where that goes. With no adapter set, every call is a no-op. That is the whole point — library authors can log freely without forcing a dependency choice on the application.

## Quick Comparison Table

| Dimension | Log::Log4perl | Log::Dispatch | Log::Any |
|---|---|---|---|
| **Layer** | Framework | Dispatcher | Facade / API |
| **Configuration** | External `.conf` (or Perl string) | Perl code | Adapter chosen by app |
| **Per-package levels** | Yes, by category name | No (per-output only) | Yes, via backend |
| **Hot reload** | Yes, `init_and_watch` | Manual | Inherited from adapter |
| **Log levels** | TRACE/DEBUG/INFO/WARN/ERROR/FATAL | debug→emerg (8 levels) | trace→fatal (8 levels) |
| **Structured output** | PatternLayout + JSON layout modules | Custom callback | Depends on adapter |
| **GitHub stars (mirror)** | 114 | 12 | 14 |
| **Last commit (2026)** | 2026-08-14 | 2026-08-04 | 2026-04-25 |
| **License** | Artistic 2.0 / GPL | Artistic 2.0 | Artistic 2.0 |
| **Best for** | Applications with ops-owned config | Embedding custom sinks | Libraries and shared code |

## Decision Matrix: Pick By Use Case

| Your situation | Pick | Why |
|---|---|---|
| Legacy app, ops team wants to change log levels without a deploy | **Log::Log4perl** | Config file plus `init_and_watch`, no code edits |
| You need a Slack/webhook sink with a custom formatter in 20 lines | **Log::Dispatch** | Outputs are objects; formatter is a coderef |
| You publish CPAN modules used by strangers | **Log::Any** | No hard dependency; silent unless the app opts in |
| Monorepo with 40 internal modules and one application | **Log::Any + Log4perl adapter** | Modules log via Log::Any, app decides the backend |
| You want a single `print` replacement with levels and no config | **Log::Dispatch** | Least ceremony to first working sink |
| You must keep two log formats during a migration | **Log::Log4perl** | Multiple appenders with independent layouts |

## Log::Log4perl — Configure Once, Change Never (Until Ops Wants To)

Log4perl's entire value proposition is that `INFO` vs `DEBUG` is a config edit, not a release. The layout below is the shape you actually deploy: root logger at `INFO` to screen, per-category override at `DEBUG` to a rotating file.

```ini
# /etc/myapp/log4perl.conf
log4perl.rootLogger              = INFO, Screen

log4perl.appender.Screen         = Log::Dispatch::Screen
log4perl.appender.Screen.stderr  = 0
log4perl.appender.Screen.layout  = PatternLayout
log4perl.appender.Screen.layout.ConversionPattern = %d{yyyy-MM-dd HH:mm:ss} %-5p [%c] %m%n

log4perl.appender.Rolling        = Log::Dispatch::FileRotate
log4perl.appender.Rolling.filename = /var/log/myapp/app.log
log4perl.appender.Rolling.mode   = append
log4perl.appender.Rolling.max    = 14
log4perl.appender.Rolling.Size   = 10485760
log4perl.appender.Rolling.layout = PatternLayout
log4perl.appender.Rolling.layout.ConversionPattern = %d{ISO8601} %p %c %m%n

log4perl.logger.MyApp.Payments   = DEBUG, Rolling
log4perl.logger.MyApp.Payments.Settlement = TRACE, Rolling
```

```perl
use strict;
use warnings;
use Log::Log4perl qw(get_logger :levels);

Log::Log4perl->init('/etc/myapp/log4perl.conf');
# During development, or when no config file is shipped:
# Log::Log4perl->easy_init($DEBUG);

my $log = get_logger('MyApp.Payments');

$log->info("batch started");
$log->debugf("job %s took %.3fs", $job_id, $elapsed);
if ($log->is_trace()) {
    $log->tracef("payload=%s", $serializer->encode($payload));
}

# Reload configuration on SIGHUP without dropping in-flight work
$SIG{HUP} = sub { Log::Log4perl->init_and_watch('/etc/myapp/log4perl.conf', 60) };
```

Three details separate a working setup from a painful one. **Use `debugf`/`tracef` rather than string interpolation** — `$log->debug($obj->dump)` builds the dump even when debug is off, and that is how logging becomes the top entry in your profiler. **Guard only the expensive paths** with `is_trace()`; `is_debug()` around every call is noise that Log4perl already handles cheaply. **`init_and_watch` re-stats the file** on the interval you pass (60 seconds above), so ops can flip a category to `DEBUG` in production and revert it a minute later.

**Where Log4perl fails you:** the config format is its own dialect, and typos fail at *runtime*, not at compile time — a misspelled appender name silently disables logging for that category. Validate your config in a test that calls `Log::Log4perl->init()` and logs to every category you care about. Also, global state means two Log4perl-initializing modules in one process can stomp on each other; initialize once in your `PSGI`/`plackup` entry point, never inside a module.

## Log::Dispatch — Build Sinks in Code, Skip the Config Language

If Log4perl is a framework, Log::Dispatch is a toolbox. You hand it an array of output specifications, and each becomes an object with its own threshold.

```perl
use Log::Dispatch;

my $log = Log::Dispatch->new(
    outputs => [
        [ 'Screen',
          min_level => 'info',
          stderr    => 0,
          newline   => 1,
          format    => sub { sprintf "%s [%s] %s", scalar(localtime), $_[1], $_[0] } ],
        [ 'File',
          min_level => 'debug',
          filename  => '/var/log/myapp/app.log',
          mode      => 'append',
          newline   => 1 ],
        [ 'Syslog',
          min_level => 'warning',
          ident     => 'myapp',
          facility  => 'daemon' ],
    ],
);

$log->info(message => 'worker pool started');
$log->log(level => 'debug', message => 'cache miss for key ' . $key);

# Cheap level check before building an expensive message
if ($log->would_log('debug')) {
    $log->debug(message => $debug_dump);
}
```

Rotating files need one more module (`Log::Dispatch::FileRotate`), and that is the honest trade-off: with Log::Dispatch you assemble the pieces yourself, which is either exactly what you want or a maintenance tax. The `format` coderef is the escape hatch for structured output — return a JSON string and every sink emits JSON.

**Where Log::Dispatch fails you:** no categories. If you want `MyApp::Payments` at `DEBUG` and everything else at `INFO`, you build that filtering yourself, usually by constructing separate dispatchers per subsystem. At that point you have reimplemented the worst third of Log4perl.

## Log::Any — The Facade That Makes Libraries Polite

Log::Any solves a social problem, not a technical one. If you publish a module and depend on Log4perl, every consumer inherits Log4perl. If you depend on Log::Any, consumers see nothing until they install an adapter.

```perl
# In your library — no backend commitment
package MyApp::Client;
use Log::Any qw($log);

sub fetch {
    my ($self, $url) = @_;
    $log->debugf("fetching %s", $url);
    my $res = $self->http->get($url);
    $log->warnf("non-2xx %d for %s", $res->code, $url) unless $res->is_success;
    return $res;
}

# In the application — choose the backend once at startup
package main;
use Log::Any::Adapter;

Log::Any::Adapter->set('File', path => '/var/log/myapp/app.log', min_level => 'debug');
# or route into an existing framework:
# Log::Any::Adapter->set('Log4perl');
# Log::Any::Adapter->set('LogDispatch', dispatcher => $dispatcher);
# Log::Any::Adapter->set('Syslog', facility => 'daemon', ident => 'myapp');

use MyApp::Client;
MyApp::Client->new->fetch('https://example.internal/health');
```

The `Log4perl` and `LogDispatch` adapters are the reason this trio composes instead of competes: adopt Log::Any in your modules today, and you can move from hand-rolled dispatchers to Log4perl config in a single startup line later, with no edits to 40 modules.

**Where Log::Any fails you:** the proxy adds a small per-call cost, and — more importantly — every level check goes through the adapter. In hot loops, hoist `if ($log->is_debug)` outside the loop. Debugging is also harder when logging is a no-op: a new developer adding `$log->info` and seeing nothing is a support ticket waiting to happen. Document that adapters exist, or set `PERL5OPT`/an env check to attach `Stdout` in development.

## Pitfalls and Migration Traps

**Double logging after an adapter change.** If a module logs via Log::Any and the app *also* initializes Log4perl with a screen appender, you get each line once through the adapter and once through any direct Log4perl logger. Audit for mixed calls before switching backends.

**`%m%n` is not a newline guarantee at your sink.** Log::Dispatch's `newline => 1` and Log4perl's pattern both add terminators. Configure exactly one, or every line ends with two newlines and your log shipper creates empty events.

**Level names differ across layers.** Log::Dispatch speaks `emerg alert crit err warning notice info debug`; Log::Any speaks `fatal alert critical error warning notice info debug trace`. A `min_level => 'error'` passed to a Log::Any adapter is not the same token as `err` in a Log::Dispatch output. Read the mapping before you copy a config between them.

**Container logging should not write files.** In Docker or Kubernetes, write to `STDOUT`/`STDERR` and let the runtime collect it. A rotating file inside a container is a full disk waiting to happen — use the `Screen` appender with `stderr => 0` and ship from the runtime.

```yaml
# docker-compose.yml — app logs to stdout, collector adds routing
services:
  app:
    image: registry.internal/myapp:2026.10
    environment:
      MYAPP_LOG_CONFIG: /etc/myapp/log4perl.conf
      MYAPP_LOG_LEVEL: info
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "5"

  vector:
    image: timberio/vector:0.44.0-alpine
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./vector.toml:/etc/vector/vector.toml:ro
    command: ["--config", "/etc/vector/vector.toml"]
```

**Do not log object dumps at INFO.** Perl's `Data::Dumper` output is multi-line; a log pipeline that assumes one event per line will mangle it into dozens of events. Serialize to single-line JSON first.

**Signal handlers and logging.** Calling a logger from a `$SIG{ALRM}` handler can re-enter an interrupted write. Defer to a queue or use `syswrite` on a preformatted string.

## FAQ

**Is Log::Log4perl still maintained in 2026?**
Yes — the repository shows commits in August 2026 and the module remains the most widely deployed Perl logging framework. Stability rather than churn is the point: configs written in 2012 still work.

**Do I need Log::Dispatch if I use Log::Log4perl?**
Indirectly, yes: Log4perl's appenders are Log::Dispatch output classes, so it is already in your dependency tree. You only write against it directly if you are constructing sinks in code.

**Can Log::Any work without any adapter installed?**
Yes. With no adapter, every log call is a no-op and returns immediately — that is why libraries can depend on it safely. The application must call `Log::Any::Adapter->set(...)` before the first log call to get output.

**Which is fastest?**
Log::Dispatch with preformatted messages is the leanest; Log::Any adds a proxy hop per call; Log4perl adds category lookup. All three are fast enough when you avoid building expensive messages at disabled levels — measure with `Devel::NYTProf` if logging shows up in your profile.

**How do I get JSON logs for a log shipper?**
Log::Log4perl: use a JSON layout module or a `PatternLayout` that emits a pre-escaped JSON string. Log::Dispatch: return a JSON string from the `format` coderef. Log::Any: choose an adapter that supports structured fields, or wrap the message in JSON before logging.

**Can I change log levels at runtime in production?**
With Log4perl, yes — `init_and_watch` plus a `SIGHUP` handler reloads per-category levels within the watch interval. With Log::Dispatch you must rebuild the dispatcher; with Log::Any it depends entirely on the adapter.

If your Perl service sits behind a framework, our [Mojolicious vs Dancer2 vs Catalyst comparison](../2026-08-01-perl-web-frameworks-mojolicious-dancer2-catalyst-comparison/) covers where each one hooks its logger in. For the ingestion side, the [rsyslog vs syslog-ng vs Vector guide](../2026-04-18-rsyslog-vs-syslog-ng-vs-vector-self-hosted-syslog-log-aggregation-guide-2026/) shows how to route these events once they leave the process. And if you are standardizing log formats across languages, our [Python structured logging comparison](../2026-07-01-python-logging-libraries-loguru-structlog-logbook-jsonlogger-picologging/) is a useful reference for field naming.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Perl Logging in 2026: Log::Log4perl vs Log::Dispatch vs Log::Any",
  "description": "A practical 2026 comparison of Perl logging modules: Log::Log4perl configuration, Log::Dispatch sinks, and the Log::Any facade, with real config files and migration traps.",
  "datePublished": "2026-10-25",
  "dateModified": "2026-10-25",
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
