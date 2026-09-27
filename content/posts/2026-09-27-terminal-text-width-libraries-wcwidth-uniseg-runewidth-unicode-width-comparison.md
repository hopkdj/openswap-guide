---
title: "Terminal Text Width in 2026: wcwidth vs uniseg vs go-runewidth vs unicode-width"
date: "2026-09-27"
tags: ["developer-tools", "unicode", "cli", "terminal", "libraries"]
draft: false
---

You shipped a CLI table. It looks perfect in your terminal — until a user pastes a Japanese project name, an emoji flag, or a Devanagari username and every column collapses into a staircase. The bug is almost never in your table renderer. It is in one line of code that assumed `len(text)` equals "how many columns this text will occupy on screen."

It does not. Python's `len("コンニチハ")` is 5. The terminal draws it in **10 columns**. Python's `len("🇩🇪")` is 2 (or more, depending on the representation), the terminal draws it in **2 columns** but as a *single* user-perceived character. Rust's `len()` counts bytes. JavaScript's `.length` counts UTF-16 code units, so `"🎉".length === 2`.

Measuring display width correctly is a solved problem — but the solution lives in five different libraries with five different APIs, and picking the wrong one produces subtly broken layouts that only appear with non-Latin input. This guide compares the five libraries that actually get installed in production in 2026, with live repository data and the real API examples from their own documentation.

## Quick Verdict (TL;DR)

- **Python:** use **`wcwidth`** — call `wcswidth(text)`, never `len(text)`, for anything that gets padded or aligned.
- **Go:** use **`rivo/uniseg`** when you care about user-perceived characters (grapheme clusters, word/line breaking) and **`mattn/go-runewidth`** when you need classic cell width with ANSI-aware truncation.
- **Rust:** use **`unicode-rs/unicode-width`** — `.width()` and `.width_cjk()` on `UnicodeWidthStr`.
- **JavaScript/Node:** use **`string-width`** — it measures visual columns *and* ignores ANSI escape sequences for free.
- **None of them agree by default on East Asian Ambiguous characters.** That is not a bug in the libraries; it is a policy decision you have to make explicitly.

If your output is pure ASCII, you can keep using `len()`. The moment emoji, CJK, or combining marks enter the picture, byte/point counting is wrong and the libraries below are the fix.

## The Comparison Table (Live Data, September 2026)

Star counts, last-push dates and descriptions below were pulled from GitHub at publication time.

| Library | Language | Stars | Last push | Spec basis | Grapheme clusters | ANSI-aware | License |
|---|---|---|---|---|---|---|---|
| [`jquast/wcwidth`](https://github.com/jquast/wcwidth) | Python + C11 | 465 | 2026-09-23 | UAX #11 + zero-width tables | Partial (newer grapheme helpers) | No (you strip first) | MIT |
| [`rivo/uniseg`](https://github.com/rivo/uniseg) | Go | 730 | 2024-05-31 | UAX #29 (graphemes, words, lines) | Yes, full segmentation | No | MIT |
| [`mattn/go-runewidth`](https://github.com/mattn/go-runewidth) | Go | 723 | 2026-09-24 | wcwidth port + East Asian tables | No | Yes (`Truncate`, `StringWidth`) | MIT |
| [`unicode-rs/unicode-width`](https://github.com/unicode-rs/unicode-width) | Rust | 318 | 2026-09-16 | UAX #11 (narrow/wide/ambiguous) | No | No | MIT / Apache-2.0 |
| [`sindresorhus/string-width`](https://github.com/sindresorhus/string-width) | JavaScript | 528 | 2026-09-24 | UAX #11 + emoji sequences | Partial (via grapheme-splitter lineage) | Yes | MIT |

Two things stand out. First, `uniseg` has not been pushed since **May 2024** — its tables are stable, but if you depend on the newest emoji being classified as wide, verify against your target set before shipping. Second, `wcwidth` is the only entry here with a native C11 core published alongside the Python package, which matters if you are measuring text in a C extension or a cgo boundary.

## Decision Matrix: Pick in 10 Seconds

| Your situation | Use | Why |
|---|---|---|
| Python CLI, tables/progress bars/padding | `wcwidth.wcswidth()` | It is the reference implementation; `-1` for control chars tells you what to strip |
| Go TUI, must truncate colored output | `go-runewidth` | `runewidth.Truncate` skips ANSI escapes so colors survive slicing |
| Go, counting user-perceived characters | `uniseg` | `GraphemeClusterCount` is UAX #29-correct for flags, ZWJ families, skin tones |
| Go, both problems at once | `uniseg` + `go-runewidth` | Cluster iteration from one, cell width from the other |
| Rust, embedded or `no_std` renderer | `unicode-width` | Zero-dependency lookup tables, `.width()` and `.width_cjk()` in one crate |
| Node CLI, output passes through chalk/picocolors | `string-width` | ANSI stripping is built in; pair with `wrap-ansi`/`slice-ansi` |
| Terminal configured for CJK (ambiguous = wide) | any of them, but call the CJK variant | `width_cjk()` / `EastAsianWidth = true` — and make it configurable |
| You only ever print ASCII logs | none | `len()` is fine; do not add a dependency for this |

## Python — wcwidth: The Reference Implementation

`wcwidth` is a port of the classic POSIX `wcwidth(3)`/`wcswidth(3)` behavior to Python (and C11), plus the Unicode tables those functions assume on modern systems. The public API is small and deliberately boring:

```python
pip install wcwidth
```

```python
from wcwidth import wcwidth, wcswidth

wcswidth("abc")          # 3
wcswidth("コンニチハ")    # 10  -> 5 fullwidth katakana, 2 columns each
wcwidth("ｱ")             # 1   -> halfwidth katakana
wcswidth("caf\u0301")    # 4   -> "cafe" + combining acute counts as one column
wcwidth("\x1b")          # -1  -> control character: not printable
```

That last line is the detail most people miss. `wcwidth()` returns **-1 for control characters**, because in the original POSIX contract they occupy no columns. If you feed a string containing ANSI color codes straight into `wcswidth()`, you get a negative contribution per escape byte and your padding math drifts. Strip or skip escapes first, or use a library that already does it.

The current development line also ships layout helpers (`align`, `wrap`, grapheme iteration, hyperlink handling) built on top of the same tables, so you do not need to bolt on a separate wrapping dependency for simple cases. Because the package caches results per code point internally, per-frame measurement in a TUI is cheap — but if you are measuring the *same* long strings every frame, cache the measured width yourself.

**Verdict for Python:** `wcwidth` is the correct default. There is no serious competitor; the only wrong answer is `len()`.

## Go — uniseg for Humans, go-runewidth for Cells

Go has two libraries because it has two distinct problems, and teams that conflate them ship broken TUIs.

**`rivo/uniseg`** implements UAX #29 — grapheme cluster, word and sentence boundaries. Its README example is the clearest demonstration of why code-point counting fails:

```go
go get github.com/rivo/uniseg
```

```go
n := uniseg.GraphemeClusterCount("🇩🇪🏳️‍🌈")
fmt.Println(n)
// 2
```

A German flag plus a rainbow flag: **2 grapheme clusters**, but many more code points and several UTF-16/UTF-8 units. If you slice that string by byte offset you can cut a ZWJ sequence in half and render two broken flags.

**`mattn/go-runewidth`** is the wcwidth lineage in Go, and its practical advantage is that it understands terminal control sequences:

```go
go get github.com/mattn/go-runewidth
```

```go
w := runewidth.StringWidth("\x1b[31mコンニチハ\x1b[0m") // measures visible cells, not escapes
s := runewidth.Truncate("コンニチハ ワールド", 8, "…")
p := runewidth.FillRight("日本", 10) // pads to exactly 10 display columns
```

The package also exposes East Asian Ambiguous handling through a package-level `EastAsianWidth` flag and a `Condition`/`CreateLUT()` API for building per-terminal tables. Because the global flag is process-wide, set it once during initialization (or use `Condition` per renderer) rather than toggling it per draw call.

**Verdict for Go:** use **both**. `uniseg` decides *where* you may cut; `go-runewidth` decides *how wide* the result is.

## Rust — unicode-width: Tables, Two Methods, No Drama

`unicode-width` is a zero-dependency crate that implements UAX #11 classification. It has no opinion about ANSI escapes (Rust terminals usually handle that via `ansi-str` or `strip-ansi-escapes`), which keeps it usable in `no_std` contexts such as embedded displays and boot loaders.

The canonical example from the crate's own documentation:

```toml
[dependencies]
unicode-width = "0.2"
```

```rust
use unicode_width::UnicodeWidthStr;

fn main() {
    let teststr = "Ｈｅｌｌｏ, ｗｏｒｌｄ!";
    let width = teststr.width();
    println!("{}", teststr);
    println!("The above string is {} columns wide.", width);

    let width = teststr.width_cjk();
    println!("The above string is {} columns wide (CJK).", width);
}
```

And the part that surprises people coming from `len()`:

```rust
use unicode_width::UnicodeWidthStr;

assert_eq!("क".width(), 1);      // Devanagari letter Ka
assert_eq!("ष".width(), 1);      // Devanagari letter Ssa
assert_eq!("क्ष".width(), 2);    // Ka + Virama + Ssa -> 3 scalars, 2 columns
```

Three Unicode scalar values, two columns. Any padding logic based on `chars().count()` over-allocates here and misaligns the whole row.

**Verdict for Rust:** `unicode-width` for measurement, plus a separate escape-stripping step. Two methods — `.width()` and `.width_cjk()` — cover both terminal conventions.

## JavaScript — string-width: The One That Already Handles Color

Node CLIs pass colored strings everywhere, which is why `string-width` is the pragmatic choice: it strips ANSI escape sequences before measuring, exactly as documented in its README.

```bash
npm install string-width
```

```javascript
import stringWidth from 'string-width';

stringWidth('a');
//=> 1
stringWidth('古');
//=> 2
stringWidth('\u001B[1m古\u001B[22m');
//=> 2
```

That third case is the one that breaks homegrown implementations: the string contains bold-on and bold-off escapes, is 12 code units long, and occupies **2 columns**. Pair it with `slice-ansi` when truncating and `wrap-ansi` when wrapping, so escapes are moved rather than cut.

**Verdict for JavaScript:** `string-width` if you render in a terminal; it is the only one of the five that needs no separate escape-stripping pass for the common case.

## The Trap: Three Definitions, One Word

"Width" means three different things, and most bugs come from mixing them:

1. **Code points / code units** — what `len()`, `.length` and `chars().count()` report.
2. **Grapheme clusters** — what a human perceives as one character (UAX #29).
3. **Display columns** — what your terminal advances the cursor by (UAX #11).

A ZWJ emoji family is 1 cluster, often 2 columns, and 7+ code points. A Devanagari conjunct is 1 cluster and 2 columns from 3 code points. Aligning a column requires definition **3**; truncating a username without breaking it requires definition **2**; and allocating a buffer requires definition **1**. Choose per operation, not per project.

## Pitfalls and Migration Notes

**East Asian Ambiguous is a policy, not a constant.** Characters like `±`, `→`, Cyrillic letters and box-drawing glyphs are 1 column in most Western terminals and 2 in many CJK-configured ones. `unicode-width` gives you `.width_cjk()`, `go-runewidth` gives you the `EastAsianWidth` flag, and `wcwidth` documents its ambiguous handling. Pick a default, expose it as a config knob, and test both modes — the "wrong" answer is inheriting whatever the library guessed.

**Variation selectors change width.** `❤` (U+2764) is narrow; `❤️` with VS16 is wide in almost every modern terminal. Never key a layout off the base code point alone.

**Control characters are not width zero — they are "not printable".** `wcwidth()` returns `-1`. Treat `-1` as `0` when summing, but log it, because it usually means an escape sequence leaked into a measured string.

**Never truncate at byte boundaries.** Slice on grapheme cluster boundaries (`uniseg`, grapheme iterators) or delegate to an ANSI-aware truncator. Cutting mid-sequence either produces invalid UTF-8 or splits a ZWJ family into visible garbage.

**Measuring per frame is a real cost.** Cache the measured width of static strings; re-measure only what changed. In Rust, precompute widths into your layout struct rather than recomputing inside the draw loop.

**Don't add a dependency for ASCII-only logs.** The common case for these libraries is user-visible layout, not log lines.

If you are doing low-level text work — encoding detection, transcoding between UTF-8/UTF-16/legacy pages — our [Unicode encoding libraries comparison](../2026-06-20-unicode-encoding-libraries-icu4c-simdutf-encoding-rs-uchardet/) covers the layer underneath this one. For producing the padded output itself, see the [string formatting libraries guide](../2026-06-20-self-hosted-string-formatting-libraries-fmtlib-icu-abseil-boost-format/), and if you are building the whole interface, the [Python terminal UI libraries comparison](../2026-07-01-python-terminal-ui-libraries-textual-rich-prompt-toolkit-urwid/) shows how Textual and Rich handle cell measurement internally.

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "TechArticle",
  "headline": "Terminal Text Width in 2026: wcwidth vs uniseg vs go-runewidth vs unicode-width",
  "description": "A hands-on comparison of terminal display-width and grapheme-cluster libraries in Python, Go, Rust and JavaScript, with live repository data and documented API examples.",
  "datePublished": "2026-09-27",
  "dateModified": "2026-09-27",
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

**Why is `len(text)` wrong for terminal alignment?**
Because `len()` counts code points or code units, not columns. Fullwidth CJK characters occupy two columns, combining marks occupy zero, and ANSI escape sequences occupy no visible space at all. Padding with `len()` misaligns as soon as any of those appear.

**What is the difference between grapheme clusters and display width?**
Grapheme clusters (UAX #29) define what a human sees as one character; display width (UAX #11) defines how many terminal columns it consumes. A flag emoji is one cluster but typically two columns; a Devanagari conjunct is one cluster and two columns made of three code points. Use clusters for cutting, columns for aligning.

**Which Go library should I use — uniseg or go-runewidth?**
Use `uniseg` for segmentation (grapheme, word and line boundaries) and `go-runewidth` for cell measurement, padding and ANSI-aware truncation. They are complementary, and serious TUIs usually import both.

**Does `string-width` handle ANSI color codes?**
Yes. It strips ANSI escape sequences before measuring, so `stringWidth('\u001B[1m古\u001B[22m')` returns `2`. Most other width libraries expect you to strip escapes yourself.

**Is `wcwidth` still maintained?**
Yes. The repository was updated in September 2026 and ships both the Python package and a C11 core. It remains the reference implementation for Python, and it also exposes layout helpers built on the same Unicode tables.

**How do I handle East Asian Ambiguous characters?**
Treat it as a configuration decision. Choose a default (usually narrow), expose a flag, and call the CJK variant when the user's terminal is configured that way. Both `unicode-width` (`width_cjk()`) and `go-runewidth` (`EastAsianWidth`) provide that switch.

---

**💰 想测试你的市场判断力？我用 [Polymarket](https://polymarket.com/?r=fc8a0) 做预测市场交易——这是全球最大的预测市场平台，从大选结果到技术监管时间线，什么都可以押注。和赌博不同，这是真正的信息市场：你懂的信息越多，胜率越高。我靠预测技术相关事件的走向已经赚了不少。用我的邀请链接注册：**[Polymarket.com](https://polymarket.com/?r=fc8a0)
