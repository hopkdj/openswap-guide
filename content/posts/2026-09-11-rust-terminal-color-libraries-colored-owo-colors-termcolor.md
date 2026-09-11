---
title: "colored vs owo-colors vs termcolor in 2026: Which Rust Terminal Color Crate Should You Ship?"
date: "2026-09-11"
tags: ["rust", "cli", "terminal", "developer-tools", "rust-crates"]
draft: false
---

Color in a CLI is a trap disguised as a feature. You add `.green()` to a success message, it looks great in your terminal, and then your users pipe output to a file, run inside CI, or use a light-background theme — and your carefully styled output becomes escape-sequence garbage or unreadable text. The Rust ecosystem has three mature answers to this problem, and they disagree about how much control you should have.

This is a comparison of **colored**, **owo-colors**, and **termcolor** as they exist in September 2026: current versions, real API differences, Windows behaviour, and the details that decide whether your CLI honors `NO_COLOR` correctly.

## TL;DR: The Quick Verdict

**Use owo-colors** for new command-line tools — it is actively maintained (last pushed 2026-08-27), works in `no_std` builds, compiles styles to constants, and ships a `supports_color` feature that handles the "should I even emit color?" question for you. **Use colored** if you want the simplest possible API and the widest mind-share in existing code; it is the crate most Rust developers already know. **Use termcolor** if you are writing a library, need explicit `WriteColor` control over where bytes go, or must support Windows consoles correctly — it is the pick behind `ripgrep` and it puts the decision in your hands instead of hiding it in a trait method.

## Side-by-Side Comparison (data pulled 2026-09-11)

| | **colored** | **owo-colors** | **termcolor** |
|---|---|---|---|
| GitHub stars | **2,036** | 809 | 491 |
| Last repo push | 2026-01-16 | 2026-08-27 | 2024-12-31 |
| Latest version | 3.1.1 | 4.4.0 | 1.4.1 |
| License | MPL-2.0 | MIT | Unlicense |
| Edition | 2021 | 2021 | 2018 |
| API style | Extension trait on `&str`/`String` | Extension trait, const-friendly | Explicit writer-based (`WriteColor`) |
| `no_std` support | No | **Yes** | No |
| Color detection | Global override only | `supports_color` / `override` features | Manual `ColorChoice` |
| Windows support | `windows-sys` dependency | Via ANSI (modern terminals) | Explicit Win32 console calls |
| Extra deps | `windows-sys` on Windows | optional (`supports-color`) | `winapi-util` on Windows |

## Which One for Which Job

| Use case | Recommended | Why |
|---|---|---|
| New CLI binary with styled human output | **owo-colors** | Small, maintained, `supports_color` handles TTY detection |
| Existing codebase already using `colored` | **colored** | No reason to churn; API is stable and familiar |
| Library that emits colored diagnostics | **termcolor** | `WriteColor` lets the caller choose the stream and policy |
| Embedded or `no_std` target | **owo-colors** | Compiles without the standard library |
| Windows console support on legacy hosts | **termcolor** | Uses Win32 console APIs rather than relying on ANSI support |
| Tests that assert exact escape sequences | **owo-colors** | `const`-evaluable styles make expected values explicit |
| Structured logs written to files | **termcolor** | Separate writer per stream avoids leaking escapes into log files |

## owo-colors: The Modern Default

owo-colors sits at 809 stars with an MIT license and saw a push on 2026-08-27; version 4.4.0 is current. Its design goals are the ones that matter for CLI work: no allocation when formatting, `no_std` compatibility, and opt-in features instead of always-on dependencies.

```toml
[dependencies]
owo-colors = { version = "4.4.0", features = ["supports-colors"] }
```

The everyday API mirrors the crate everybody already knows:

```rust
use owo_colors::OwoColorize;

fn main() {
    println!("{}", "build succeeded".green().bold());
    println!("{}", "warning: cache miss".yellow());
    eprintln!("{}", "error: cannot open config".red().underline());
}
```

Because styles can be `const`, you can define them once and reuse them without constructing anything at runtime:

```rust
use owo_colors::{OwoColorize, Style};

const SUCCESS: Style = Style::new().green().bold();
const FAILURE: Style = Style::new().red().bold();

fn report(ok: bool, msg: &str) {
    let style = if ok { SUCCESS } else { FAILURE };
    println!("{}", msg.style(style));
}
```

Where owo-colors pulls ahead of the older crates is color policy. With the `supports-colors` feature you answer the "is this a terminal that wants color?" question explicitly:

```rust
use owo_colors::{OwoColorize, Stream};
use owo_colors::Stream::Stdout;

fn main() {
    // Respects NO_COLOR, FORCE_COLOR, and TTY detection
    if Stdout.supports_colors() {
        println!("{}", "color enabled".green());
    } else {
        println!("color enabled");
    }
}
```

There is also a global override for tests and for `--color=always` style flags:

```rust
owo_colors::set_override(true);  // force color on
```

**Where it hurts:** the ecosystem is younger than the alternatives, so when you search for an answer you will find fewer posts. Windows support relies on the terminal understanding ANSI escapes, which is true for Windows Terminal and modern console hosts but not for every legacy environment. If your binary must run on ancient Windows shells, that is a real constraint rather than a theoretical one.

## colored: The Familiar One

colored is the crate most Rust developers learned first — 2,036 stars, MPL-2.0, version 3.1.1, with the repository last pushed 2026-01-16. It stays popular because its API is one import away from feeling like part of the standard library.

```toml
[dependencies]
colored = "3.1.1"
```

```rust
use colored::Colorize;

fn main() {
    println!("{}", "deploy".cyan().bold());
    println!("{}", "failed".on_red().white());
    println!("{}", "3 files changed".underline());
}
```

colored also supports nested styling and a few conveniences that make it pleasant for interactive tools — clearing styles, combining background colors, and styling `String` values in place:

```rust
use colored::Colorize;

let mut line = String::from("tests passed");
line = line.green().to_string();
println!("{line}");

// Subtle output for a diff-like view
println!("{} {}", "+ added".green(), "- removed".red());
```

```rust
use colored::control;

fn main() {
    control::set_override(true);   // force escapes for tests
    println!("{}", "always colored".blue());
    control::unset_override();     // return to auto-detection
}
```

**Where it hurts:** color policy is coarse. colored detects whether stdout is a TTY on its own and gives you a single global override; there is no per-stream decision, so writing colored text into a file that a log collector reads requires you to bypass the crate. On Windows it pulls in `windows-sys` (with `Win32_Foundation` and `Win32_System_Console` features) to configure the console, which adds a platform dependency to your build graph. Maintenance has slowed compared with owo-colors, though the API is stable enough that this rarely bites.

## termcolor: The Library Author's Choice

termcolor (491 stars, Unlicense, version 1.4.1, last pushed 2024-12-31) is the most conservative of the three and the most explicit. It was written by the author of `ripgrep`, and its design reflects the needs of a tool that writes to multiple streams under a policy the user chose on the command line.

```toml
[dependencies]
termcolor = "1.4.1"
```

Instead of decorating strings, you decorate a writer:

```rust
use termcolor::{BufferWriter, Color, ColorChoice, ColorSpec, WriteColor};
use std::io::Write;

fn main() -> std::io::Result<()> {
    let mut out = BufferWriter::stdout(ColorChoice::Auto).buffer();

    let mut spec = ColorSpec::new();
    spec.set_fg(Some(Color::Green)).set_bold(true);
    out.set_color(&spec)?;
    write!(out, "build succeeded")?;
    out.reset()?;
    writeln!(out)?;

    BufferWriter::stdout(ColorChoice::Auto).print(&out)?;
    Ok(())
}
```

The `ColorChoice` enum is the point: `Always`, `Never`, and `Auto` are decisions your caller makes, not decisions hidden inside a library. `BufferWriter` also buffers entire blocks of output before writing, which avoids interleaving artifacts when several threads print to the same terminal.

For per-stream control — a common requirement when stdout is a terminal but stderr is redirected — you create two writers with two policies:

```rust
use termcolor::{ColorChoice, StandardStream};

let mut stdout = StandardStream::stdout(ColorChoice::Auto);
let mut stderr = StandardStream::stderr(ColorChoice::Auto);
```

Libraries that use termcolor integrate cleanly into tools with a `--color=auto|always|never` flag, because the flag maps directly onto `ColorChoice`.

**Where it hurts:** it is more code for trivial output, and the repository has not been updated since the end of 2024 — a sign of stability rather than neglect, but it does mean new ANSI features land elsewhere first. There is no built-in `NO_COLOR` handling: you read the environment variable yourself and translate it into a `ColorChoice`, which is arguably correct for a library but is work you must remember to do.

## Getting Color Policy Right

All three crates produce escape sequences; only two of them answer the harder question. The convention users expect in 2026 is straightforward, and it is worth implementing regardless of which crate you choose:

- Honor `NO_COLOR` when it is set to any non-empty value — this is a cross-tool convention, not a Rust-specific one.
- Honor `FORCE_COLOR` when output is redirected but the user asked for color anyway.
- Detect TTY support automatically as the default.
- Let an explicit CLI flag (`--color=never`) override everything else.

owo-colors ships this behaviour behind the `supports-colors` feature. termcolor gives you the primitives to implement it in about fifteen lines. colored gives you a single global switch, which is enough for small tools and not enough for tools with three output streams.

If you are comparing how other Rust libraries handle configuration and style at the same layer, our [Rust observability stack guide](../2026-07-23-rust-observability-tracing-opentelemetry-metrics/) shows where color and log formatting interact, and our [cross-language logging library comparison](../2026-06-20-logging-libraries-spdlog-logrus-zerolog-serilog-winston-logback/) puts structured output next to console output where the two usually collide. For the same decision in another ecosystem, see our [Node.js terminal color libraries benchmark](../2026-09-10-nodejs-terminal-color-libraries-chalk-kleur-picocolors-benchmark/) — the trade-offs between sugar, tree-shaking, and policy repeat almost exactly.

## Pitfalls: Where CLI Color Goes Wrong

1. **Color in piped output breaks parsers.** When stdout is not a TTY, emit plain text. Every grep-and-awk pipeline in the world depends on it, and so does CI log search.
2. **`NO_COLOR` is not the same as `TERM=dumb`.** Check both conventions; a user setting `NO_COLOR=1` expects no escapes even if `TERM` is a full-featured terminal.
3. **Escape sequences count toward width.** If you use `colored` or `owo-colors` to build padded tables, the padding math must use the uncolored string length. Compute width first, then colorize.
4. **Windows needs more than ANSI.** Legacy console hosts require Win32 console calls; termcolor handles that path explicitly, the trait-based crates assume the terminal does.
5. **Styled text in log files is noise.** If a log line can be redirected to a file, colorize the terminal writer only. This is exactly the case termcolor's multi-writer design exists for.
6. **Global overrides leak between tests.** `set_override(true)` is process-wide state; tests that run in parallel and assert on escape sequences will interfere with each other unless you serialize them.
7. **Dependencies return through feature flags.** owo-colors keeps `no_std` clean only if you leave the detection features off; enabling `supports-colors` pulls in the environment-detection crates. Check `cargo tree` before shipping a size-sensitive binary.

## FAQ

**Which Rust color crate is fastest?**
Formatting cost is dominated by your own I/O, not by the styling crate; all three compile down to string writes with escape sequences. owo-colors avoids allocation by design and termcolor buffers whole blocks, so the practical difference shows up in throughput-heavy output rather than in a single `println!`.

**Should I use `colored` or `owo-colors` for a new project?**
owo-colors, unless you specifically want the smallest API surface. It is more actively maintained, supports `no_std`, and ships color-policy detection that you would otherwise write yourself.

**Does `termcolor` support `NO_COLOR`?**
Not automatically. You read the environment variable and translate it to `ColorChoice::Never`; the crate deliberately leaves that policy decision to the application.

**Can I use these crates in a library that others depend on?**
Using termcolor is the safest choice because it exposes `WriteColor` and lets the consuming application choose the policy and the stream. Emitting styled strings from a library forces the caller to strip escape codes if they disagree.

**How do I test colored output in Rust?**
Set a global override (`set_override(true)` in owo-colors or `control::set_override(true)` in colored) so the escape sequences are emitted even though the test harness is not a TTY, then compare the string against the expected sequence. Run those tests serially, since the override is process-wide.

**What about `nu-ansi-term` and `anstyle`?**
Both are worth knowing. `nu-ansi-term` (from the Nushell project) is a maintained fork of the abandoned `ansi_term` crate, and `anstyle` (from the `rust-cli` organization) is a style-description crate designed to be dependency-light for use inside other libraries. Neither has the same install base as the three compared here, but both are reasonable choices inside their niches.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "colored vs owo-colors vs termcolor in 2026: Which Rust Terminal Color Crate Should You Ship?",
  "description": "Comparison of the colored, owo-colors, and termcolor crates for Rust CLI development in 2026 — versions, licenses, no_std support, color policy handling, and real code examples.",
  "datePublished": "2026-09-11",
  "dateModified": "2026-09-11",
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
