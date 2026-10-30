---
title: "Go Terminal Styling in 2026: Lipgloss vs fatih/color vs Aurora"
date: "2026-10-31"
tags: ["go", "golang", "cli-tools", "terminal", "developer-tools"]
draft: false
cover: "/img/screenshots/aurora-terminal-colors.jpg"
---

Your Go CLI prints grey text on a black background, and users assume it is a toy. That single aesthetic decision costs you adoption before anyone reads your `--help` output. Terminal styling is not decoration — it is how a CLI signals which line is an error, which row is selected, and where the eye should land first.

The Go ecosystem has three serious answers, and they disagree about almost everything: **Charmbracelet's Lipgloss (11,964 stars)** treats the terminal as a layout canvas, **fatih/color (8,006 stars)** treats it as a `Printf` with colors, and **Aurora (1,494 stars)** treats it as a byte stream that should never allocate more than necessary. Picking the wrong one means either fighting a styling engine for simple colored logs, or hand-rolling box drawing for a dashboard.

## TL;DR — The 30-Second Verdict

- **Building a TUI dashboard, table, or anything with borders, padding, and alignment?** Use **Lipgloss**. Nothing else in Go measures ANSI-aware string widths for you, and that is the exact problem you will hit on day two.
- **Adding colored log levels or warnings to an existing CLI in ten minutes?** Use **fatih/color**. It is one import, `color.Red("...")`, done. No layout model to learn.
- **Shipping a zero-dependency binary you want to vendor forever without churn?** Use **Aurora**. No transitive modules, no cgo, and one small API that has stayed stable since v3.0.0 in 2020.
- **You are on Lipgloss v1 today?** Read the migration section below before you upgrade. v2 moved to a new module path, deleted `Renderer`, and turned `Color` from a type into a function.

## The Three Contenders at a Glance

All figures below were pulled live from GitHub and the Go module proxy on 2026-10-31.

| | **Lipgloss** | **fatih/color** | **Aurora** |
|---|---|---|---|
| Stars | 11,964 | 8,006 | 1,494 |
| Latest version | v2.0.6 (Aug 2026) | v1.19.0 (Mar 2026) | v3.0.0 (Jul 2020) |
| Last commit | 2026-10-11 | 2026-10-12 | 2026-10-24 |
| License | MIT | MIT | Unlicense |
| Transitive deps | Pure Go | `go-colorable`, `go-isatty` | None |
| Layout engine | Yes — width, padding, borders, join, place | No | No |
| Color depth | Truecolor + adaptive light/dark | 8/16-color attributes, raw SGR for 256/truecolor | 16-color, 256-color via `Index`, truecolor via `RGB` |
| Windows handling | Native ANSI, no shim | `go-colorable` shim for legacy consoles | Native ANSI |
| API surface | Large (styles, tables, trees, lists, canvas) | Tiny | Small |

Two numbers matter more than the rest. **Lipgloss has 5,400 more stars than fatih/color and roughly 8x Aurora's count**, which reflects where the Bubble Tea ecosystem funneled attention. But **Aurora has 1,494 stars with zero commits breaking its API in six years** — a different kind of value that star counts do not capture.

## Decision Matrix: Pick in Ten Seconds

| Your situation | Pick | Why |
|---|---|---|
| TUI with panes, borders, or side-by-side columns | **Lipgloss** | `Width`, `Padding`, `Border`, `JoinHorizontal`, `Place` — you cannot fake this with escape codes |
| Wrap existing `fmt.Printf` logging with severity colors | **fatih/color** | `color.Red(...)` is a drop-in; `color.New(...).Printf` keeps format verbs |
| Statically linked binary for Alpine/scratch, minimal deps | **Aurora** | Zero transitive modules; nothing to vet in `go.sum` |
| Must support old Windows Server consoles | **fatih/color** | `go-colorable` translates ANSI to Win32 console calls |
| Adaptive colors that differ in light vs dark terminals | **Lipgloss v2** | `LightDark` / `compat.AdaptiveColor` handle detection for you |
| Table rendering with aligned columns | **Lipgloss v2** | The `table` subpackage does ANSI-aware column math |
| Chained `Sprintf`-style composition with no allocations you can see | **Aurora** | Methods return values that thread through `Printf` verbs |
| You need it working in 15 minutes, not perfect | **fatih/color** | Smallest conceptual surface of the three |

## Lipgloss: Treating the Terminal as a Canvas

Lipgloss is the reason Go CLIs started looking like this decade. Its core insight is that **ANSI escape codes break `len()`** — a red string is longer than its visible characters, so naive padding produces misaligned boxes. Lipgloss measures visible width and compensates.

Here is the current v2 install path. Note that it is **not** `github.com/charmbracelet/lipgloss` anymore:

```bash
go get charm.land/lipgloss/v2
```

A working card renderer with a gradient border and a clickable hyperlink, using v2 APIs:

```go
package main

import (
	"charm.land/lipgloss/v2"
)

var card = lipgloss.NewStyle().
	Bold(true).
	Foreground(lipgloss.Color("#FAFAFA")).
	Background(lipgloss.Color("#7D56F4")).
	Padding(1, 3).
	Width(28)

var box = lipgloss.NewStyle().
	Border(lipgloss.RoundedBorder()).
	BorderForegroundBlend(lipgloss.Color("#7D56F4"), lipgloss.Color("#04B575")).
	Padding(0, 1)

func main() {
	label := card.Render("BUILD OK")
	s := box.Render(label)
	lipgloss.Println(s) // NOT fmt.Println — see the downsampling note below
}
```

That `lipgloss.Println` line is the single most common v2 mistake. In v1 you could `fmt.Println(style.Render(x))`. In v2 you must print through Lip Gloss's writer, because **color downsampling now happens at write time**: a truecolor style sent to a 256-color terminal gets converted instead of emitted as unsupported SGR.

The second thing Lipgloss buys you is layout composition:

```go
row := lipgloss.JoinHorizontal(lipgloss.Top,
	lipgloss.NewStyle().Width(20).Render("cpu   42%"),
	lipgloss.NewStyle().Width(20).Render("mem   61%"),
	lipgloss.NewStyle().Width(20).Render("disk  88%"),
)

// Center a block in an 80x24 viewport
centered := lipgloss.Place(80, 24, lipgloss.Center, lipgloss.Center, row)
```

`JoinHorizontal` aligns blocks of differing heights. `Place` centers arbitrary content in a fixed viewport — the function every splash screen needs and nobody wants to write.

**Where Lipgloss hurts:** it is a large API. Styles are value types that you copy around, and composing deeply nested styles produces code that reads like CSS in Go. If all you need is a red error message, you will have imported a layout engine to print one line.

![Aurora terminal color output](/img/screenshots/aurora-hyperlinks-terminal.jpg "Terminal hyperlink flags rendered by Aurora — the same escape sequences every Go styling library emits")

## fatih/color: The Pragmatic Workhorse

fatih/color has been the default answer since 2014 and it still is, because the API fits in your head:

```go
import "github.com/fatih/color"

color.Red("connection refused: %s", addr)
color.Green("applied %d changes", n)

warn := color.New(color.FgYellow, color.Bold)
warn.Printf("deprecated flag %q ignored\n", flag)

errStyle := color.New(color.FgHiWhite, color.BgRed).SprintFunc()
fmt.Fprintln(os.Stderr, errStyle("FATAL: disk full"))
```

Three properties make it sticky in existing codebases:

1. **`Printf` semantics are preserved.** You keep format verbs and do not build strings first.
2. **Global kill switch.** `color.NoColor = true` (or the `NO_COLOR` env var, which it honors) disables everything — essential for CI logs and `| less` pipelines.
3. **Windows actually works.** `go-colorable` + `go-isatty` mean old consoles get translated calls rather than raw escape garbage.

For 256-color and truecolor you drop to raw attribute values, which is where the ergonomics fall off:

```go
// 256-color: SGR 38;5;<n>
orange := color.New(color.Attribute(38), color.Attribute(5), color.Attribute(208))
// truecolor: SGR 38;2;<r>;<g>;<b>
brand := color.New(color.Attribute(38), color.Attribute(2),
	color.Attribute(0x7D), color.Attribute(0x56), color.Attribute(0xF4))
```

**Where fatih/color hurts:** no width awareness at all. Pad a colored string and your table breaks. There is also no scoping model — every style is either global state or a `*color.Color` you thread manually, and nested styles overwrite rather than compose.

## Aurora: Zero Dependencies, Zero Surprises

Aurora's pitch is architectural rather than aesthetic. It is a **single package with no transitive modules**, licensed under the Unlicense, and its public API has not broken since v3.0.0 shipped in July 2020.

```go
import "github.com/logrusorgru/aurora/v3"

au := aurora.NewAurora(true) // true = colorize; false = pass through plain text

fmt.Println(au.Bold(au.Green("OK")))
fmt.Println(au.BgRed(au.Bold("FAIL")))
fmt.Printf("%s deployed to %s\n", au.Cyan(release), au.Magenta(region))
```

Aurora's design trick is that every value satisfies `fmt.Formatter`, so styles thread directly through `Printf` verbs without intermediate strings:

```go
// composable without building a string per segment
fmt.Printf("%s %s\n", au.Bold("step 3/7"), au.Index(208, "warming cache"))
fmt.Println(au.RGB(0x7d, 0x56, 0xf4, "truecolor works too"))
```

`aurora.NewAurora(bool)` is also the cleanest testability story of the three: construct with `false` in tests and assert on plain strings with no escape codes to strip.

**Where Aurora hurts:** it is a **color library, not a layout library**. No padding, no borders, no width measurement. It also gets the least attention — last tagged release is 2020, so while commits continue (most recently 2026-10-24), fixes land on `master` without a version bump. If your policy forbids depending on untagged code, that is a real blocker.

## Migration Notes and Pitfalls (Read Before You Upgrade)

This section is where most people get burned, so it is worth reading even if you skimmed everything above.

### 1. Lipgloss v2 changed the module path — `@latest` lies

If you run `go get github.com/charmbracelet/lipgloss`, the module proxy reports **v1.1.0** as the newest version. That is misleading: v2 lives on a **vanity import path** and will never appear under the old one.

| Item | v1 | v2 |
|---|---|---|
| Import path | `github.com/charmbracelet/lipgloss` | `charm.land/lipgloss/v2` |
| Subpackages | `.../lipgloss/table` | `charm.land/lipgloss/v2/table` |
| Latest tag | v1.1.0 (Mar 2025) | v2.0.6 (Aug 2026) |

The migration is mechanical — a search-and-replace of `github.com/charmbracelet/lipgloss` → `charm.land/lipgloss/v2` gets you most of the way — but the API removals do not compile away quietly.

### 2. `Color` became a function, and `Renderer` was deleted

The two changes that break real code:

```go
// v1: Color was a TYPE, so this was legal
var c lipgloss.Color = "#7D56F4"

// v2: Color is a FUNCTION returning color.Color
c := lipgloss.Color("#7D56F4")
```

Everything tied to renderers is gone in v2: `Renderer`, `NewRenderer`, `DefaultRenderer`, `SetDefaultRenderer`, and `renderer.NewStyle()`. `NewStyle()` now returns a plain value with no renderer binding, which is simpler — but any code holding a `*lipgloss.Renderer` will not compile.

Other silent removals worth grepping for: `ColorProfile()` (use `colorprofile.Detect(w, env)`), `SetColorProfile`, `SetHasDarkBackground`, `type TerminalColor` (use `image/color.Color`), and `type AdaptiveColor` (now `compat.AdaptiveColor` or `LightDark`).

### 3. Adaptive colors need the `compat` package

```go
import (
	"charm.land/lipgloss/v2"
	"charm.land/lipgloss/v2/compat"
)

color := compat.AdaptiveColor{
	Light: lipgloss.Color("#f1f1f1"),
	Dark:  lipgloss.Color("#cccccc"),
}
```

The `compat` package reads `stdin`/`stdout` globally exactly like v1 did. To control detection explicitly, set `compat.HasDarkBackground` and `compat.Profile` in an `init()`.

### 4. Do not `fmt.Println` a Lipgloss v2 style

Covered above, repeated here because it fails silently: colors look fine on your truecolor laptop and render as garbage or plain text on a 256-color terminal or inside `tmux` with a limited profile. Use `lipgloss.Println` (or Bubble Tea v2, which handles it for you).

### 5. fatih/color's globals bite in libraries, not in binaries

`color.NoColor` is package-level state. In an application that is fine and convenient. In a **library** that other people import, flipping it changes their output too. If you are publishing a package, accept a `*color.Color` parameter instead of touching the global.

### 6. Aurora's pass-through flag is not a no-op flag

`aurora.NewAurora(false)` still returns styled values — they simply carry no escape codes. That is what you want for tests and for `NO_COLOR` compliance, but it means your assertions become plain-string comparisons, so write them against visible text, not against `\x1b[` prefixes.

### 7. Do not mix libraries in one output stream

Each library manages its own reset sequences. Interleaving Aurora-styled and Lipgloss-styled output in the same line can leave a dangling background color that bleeds into the next line. Pick one per program, or wrap the secondary library's output in a `\x1b[0m` reset.

## FAQ

**Which Go terminal styling library is fastest?**

Speed is rarely the bottleneck, but structurally Aurora does the least work per call — it appends bytes to an internal buffer and allocates no style objects. fatih/color caches `SprintfFunc` closures per style, so repeated formatting is cheap. Lipgloss does the most work because it must compute visible width by scanning for escape sequences, which is the price of correct alignment. If you are styling millions of lines, prefer Aurora or fatih/color; if you are rendering a 24-line dashboard, the difference is unmeasurable.

**Is Lipgloss v2 stable enough for production?**

v2.0.6 shipped on 2026-08-11 after a documented migration guide and a `compat` shim for the most common v1 patterns. It is the actively developed line: commits continue through October 2026 while v1.1.0 has not been tagged since March 2025. New projects should start on v2 at `charm.land/lipgloss/v2`; existing v1 projects can migrate deliberately using the search-and-replace path plus the removals list above.

**Can I use fatih/color and Lipgloss together?**

Technically yes, and people do — fatih/color for log lines emitted by libraries, Lipgloss for the TUI frame. The risk is reset-sequence interference: a missing reset from one library tints output rendered by the other. If you must combine them, render each library's output as a complete string and print it on its own line rather than concatenating styled fragments mid-line.

**Does Aurora support truecolor?**

Yes. `aurora.RGB(r, g, b, v)` emits 24-bit SGR sequences, and `aurora.Index(n, v)` emits 256-color palette codes. Both compose with attribute wrappers like `au.Bold(...)` and thread through `fmt` verbs because aurora values implement `fmt.Formatter`.

**Which library should I use for a table in a CLI?**

Lipgloss, unambiguously. Its `table` subpackage (now `charm.land/lipgloss/v2/table`) handles ANSI-aware column widths, borders, and per-cell styles. Neither fatih/color nor Aurora measures string width, so building an aligned table on top of either means writing your own escape-sequence-aware `len()` — which is exactly the bug Lipgloss was created to fix.

**Do these libraries respect `NO_COLOR` and non-TTY output?**

fatih/color does out of the box: it honors `NO_COLOR` and disables itself when stdout is not a terminal, and `color.NoColor = true` forces it off. Lipgloss v2 handles it through profile detection at write time via `lipgloss.Println`. Aurora requires you to pass `false` to `NewAurora` yourself, typically wired to an `isatty` check — more explicit, less magic.

## Related Reading

Terminal styling is one slice of a bigger picture. If you are choosing output libraries across stacks, our [Node.js terminal color library benchmark](../2026-09-10-nodejs-terminal-color-libraries-chalk-kleur-picocolors-benchmark/) covers chalk, kleur, and picocolors with real numbers, and the [Rust terminal color comparison](../2026-09-11-rust-terminal-color-libraries-colored-owo-colors-termcolor/) covers colored, owo-colors, and termcolor. If what you actually need is color-space math rather than ANSI output — palette generation, perceptual gradients, contrast ratios — see our [color manipulation library comparison](../2026-10-05-color-manipulation-libraries-chromajs-culori-palette-go-colorful/) covering chroma.js, culori, and go-colorful.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Go Terminal Styling in 2026: Lipgloss vs fatih/color vs Aurora",
  "description": "A hands-on comparison of Go terminal styling libraries: Lipgloss v2, fatih/color, and Aurora, with real version data, code samples, a v1-to-v2 migration table, and a decision matrix.",
  "datePublished": "2026-10-31",
  "dateModified": "2026-10-31",
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
